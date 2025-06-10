import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pypdf import PdfReader, PdfWriter
from PyPDF2.generic import NameObject, createStringObject
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache

class PDFMetadataEditor:
    def __init__(self):
        self.pdf_cache = {}
        self.folders = []
        self.current_popup = None # To store a reference to the current popup window

    @lru_cache(maxsize=1000)
    def extract_metadata_from_filename(self, filename):
        """Cached filename parsing"""
        match = re.match(r"(.+?) - (.+?)\.pdf$", filename)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return "", os.path.splitext(filename)[0]

    def extract_metadata_from_pdf_safe(self, path):
        """Safe PDF metadata extraction with caching"""
        if path in self.pdf_cache:
            return self.pdf_cache[path]

        try:
            reader = PdfReader(path)
            info = reader.metadata
            result = (info.get("/Title", "").strip(), info.get("/Author", "").strip())
            self.pdf_cache[path] = result
            return result
        except Exception as e:
            print(f"Error reading {path}: {e}")
            result = ("", "")
            self.pdf_cache[path] = result
            return result

    def process_single_pdf(self, file_info):
        """Process a single PDF file - designed for threading"""
        root, filename = file_info
        full_path = os.path.join(root, filename)

        fn_author, fn_title = self.extract_metadata_from_filename(filename)
        meta_title, meta_author = self.extract_metadata_from_pdf_safe(full_path)

        return {
            "path": full_path,
            "filename": filename,
            "fn_title": fn_title,
            "fn_author": fn_author,
            "meta_title": meta_title,
            "meta_author": meta_author
        }

    def collect_pdfs_recursively(self, folder, progress_callback=None):
        """Threaded PDF collection with progress updates"""
        pdf_files = []
        file_list = []

        print(f"Scanning for PDFs in: {folder}")

        # First pass: collect all PDF file paths (fast)
        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(".pdf"):
                    file_list.append((root, f))

        if not file_list:
            return pdf_files

        print(f"Found {len(file_list)} PDF files, processing metadata...")

        # Second pass: process metadata in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_file = {executor.submit(self.process_single_pdf, file_info): file_info
                             for file_info in file_list}

            completed = 0
            for future in as_completed(future_to_file):
                try:
                    result = future.result()
                    pdf_files.append(result)
                    completed += 1

                    if progress_callback:
                        progress_callback(completed, len(file_list))

                except Exception as e:
                    file_info = future_to_file[future]
                    print(f"Error processing {file_info}: {e}")

        return pdf_files

    def update_pdf_metadata_batch(self, updates):
        """Batch update PDF metadata with threading"""
        def update_single(update_info):
            path, title, author = update_info
            try:
                reader = PdfReader(path)
                writer = PdfWriter()

                for page in reader.pages:
                    writer.add_page(page)

                writer.add_metadata({
                    "/Title": title,
                    "/Author": author
                })

                writer._root_object.update({
                    NameObject("/Pages"): writer._pages
                })

                temp_path = path + ".temp.pdf"
                with open(temp_path, "wb") as f:
                    writer.write(f)

                os.replace(temp_path, path)

                # Update cache
                self.pdf_cache[path] = (title, author)
                return True
            except Exception as e:
                print(f"Failed to update {path}: {e}")
                return False

        successful_updates = 0
        with ThreadPoolExecutor(max_workers=2) as executor:  # Fewer workers for writing
            futures = [executor.submit(update_single, update) for update in updates]
            for future in as_completed(futures):
                if future.result():
                    successful_updates += 1

        return successful_updates

    def browse_folders(self):
        # Modified: Only allow selection of a single folder at a time
        folder = filedialog.askdirectory(title="Select Folder Containing PDFs")
        if not folder:
            sys.exit(0) # Exit if no folder selected

        self.folders = [folder] # Now self.folders will contain a single folder
        self.show_progress_and_collect()

    def show_progress_and_collect(self):
        """Show progress dialog while collecting PDFs"""
        progress_window = tk.Toplevel()
        progress_window.title("Scanning PDFs...")
        progress_window.geometry("400x150")
        progress_window.transient()
        progress_window.grab_set()
        self.current_popup = progress_window # Store reference to this popup
        progress_window.configure(bg="#333333") # Dark background for progress window

        tk.Label(progress_window, text="Scanning folders for PDF files...", font=('Arial', 10), bg="#333333", fg="#D3D3D3").pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
        progress_bar.pack(pady=10, padx=20, fill="x")

        status_label = tk.Label(progress_window, text="Initializing...", font=('Arial', 9), bg="#333333", fg="#D3D3D3")
        status_label.pack(pady=5)

        pdf_data = []

        def update_progress(current, total):
            progress = (current / total) * 100
            progress_var.set(progress)
            status_label.config(text=f"Processing {current}/{total} files...")
            progress_window.update()

        def collect_data():
            nonlocal pdf_data
            try:
                for folder in self.folders:
                    folder_data = self.collect_pdfs_recursively(folder, update_progress)
                    pdf_data.extend(folder_data)
                progress_window.destroy()
                self.current_popup = None # Clear reference
                self.show_results(pdf_data, os.path.basename(self.folders[0])) # Display selected folder name
            except Exception as e:
                progress_window.destroy()
                self.current_popup = None # Clear reference
                messagebox.showerror("Error", f"Error collecting PDF data: {e}")

        # Start collection in thread to prevent UI freezing
        thread = threading.Thread(target=collect_data, daemon=True)
        thread.start()

    def select_another_folder(self):
        """Method to select another folder and refresh the view."""
        if self.current_popup:
            self.current_popup.destroy() # Close the currently active popup
            self.current_popup = None
        self.browse_folders() # Call browse_folders to start the process again

    def refresh_data(self, popup, tree):
        """Rescan folders and refresh the tree view"""
        # Clear cache for accurate refresh
        self.pdf_cache.clear()
        
        # Store current popup reference before destroying it
        self.current_popup = popup
        popup.destroy()  # Close current window
        self.current_popup = None # Clear reference after destroying
        self.show_progress_and_collect()  # Show new progress window and collect

    def show_results(self, data, folder_name):
        popup = tk.Toplevel()
        popup.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
        popup.title(f"PDF Metadata Editor – {folder_name} ({len(data)} files)")
        popup.geometry("1000x600")
        popup.configure(bg="#333333") # Dark background
        self.current_popup = popup # Store reference to this popup

        # Add a frame for the Treeview with scrollbars
        frame = tk.Frame(popup, bg="#333333") # Dark background for frame
        frame.pack(expand=True, fill="both", padx=10, pady=10)

        style = ttk.Style()
        # Frutiger Aero inspired styling for dark mode
        style.theme_use('vista') # 'vista' or 'xpnative' often provide a good base
        
        # Treeview styling for dark mode
        style.configure("Treeview",
                        background="#2C2C2C", # Darker background for treeview
                        foreground="#FFFFFF", # White text
                        rowheight=25,
                        fieldbackground="#2C2C2C",
                        font=('Arial', 9))
        style.map('Treeview', background=[('selected', '#0078D7')], # Vibrant blue on selection
                               foreground=[('selected', '#FFFFFF')]) # White text on selection
        style.configure("Treeview.Heading",
                        font=('Arial', 10, 'bold'),
                        background="#1F1F1F", # Even darker heading background
                        foreground="#D3D3D3") # Light gray heading text

        # Button styling for dark mode - adjusted foreground for higher contrast
        style.configure("TButton",
                        font=('Arial', 10, 'bold'),
                        background="#0078D7", # Vibrant Blue
                        foreground="#1A1A1A", # Very dark gray text for contrast
                        padding=8,
                        relief="raised",
                        borderwidth=2,
                        focusthickness=3,
                        focuscolor="")
        style.map("TButton",
                  background=[('active', '#0056B3')]) # Darker blue on hover
        
        # Configure the base TProgressbar style directly for dark mode
        style.configure("TProgressbar",
                        background="#00BFFF", # Deep Sky Blue for progress bar
                        troughcolor="#1A1A1A") # Very dark trough

        tree = ttk.Treeview(frame, columns=("fn_title", "fn_author", "meta_title", "meta_author"),
                            show="headings", selectmode="extended", style="Treeview")

        tree.heading("fn_title", text="Filename Title")
        tree.heading("fn_author", text="Filename Author")
        tree.heading("meta_title", text="Metadata Title")
        tree.heading("meta_author", text="Metadata Author")

        for col in ("fn_title", "fn_author", "meta_title", "meta_author"):
            tree.column(col, width=200 if "title" in col else 150, anchor="w")

        # Scrollbars
        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        tree.pack(expand=True, fill="both")

        def swap_fn_title_author():
            for item in tree.selection():
                values = list(tree.item(item)["values"])
                # Ensure we only swap the first two values (filename title/author)
                if len(values) >= 2:
                    values[0], values[1] = values[1], values[0]
                    tree.item(item, values=values)

        # Insert data efficiently
        mismatch_count = 0
        for entry in data:
            row = (entry["fn_title"], entry["fn_author"], entry["meta_title"], entry["meta_author"])
            tags = [entry["path"]]
            mismatch = row[0] != row[2] or row[1] != row[3]
            if mismatch:
                mismatch_count += 1
                tags.append("mismatch")
            tree.insert("", "end", values=row, tags=tags)

        tree.tag_configure("mismatch", background="#B00020", foreground="#FFFFFF") # Dark red for mismatch, white text

        # Add editable cells
        def on_double_click(event):
            item_id = tree.identify_row(event.y)
            column = tree.identify_column(event.x)
            # Only allow editing for filename title and author columns
            if column not in ("#1", "#2"):
                return

            # Ensure item_id is valid
            if not item_id:
                return

            x, y, width, height = tree.bbox(item_id, column)
            if x is None: # Sometimes bbox returns None if item is not visible
                return

            entry = ttk.Entry(tree, style="TEntry") # Use ttk.Entry for consistent styling
            entry.place(x=x, y=y, width=width, height=height)
            entry.insert(0, tree.set(item_id, column))
            entry.focus()

            def save_edit(event=None):
                tree.set(item_id, column, entry.get())
                entry.destroy()

            entry.bind("<Return>", save_edit)
            entry.bind("<FocusOut>", save_edit)

        tree.bind("<Double-1>", on_double_click)

        # Fix selected metadata with batch processing
        def fix_selected_metadata():
            if not tree.selection():
                messagebox.showwarning("No Selection", "Please select files to update.")
                return

            updates = []
            for item in tree.selection():
                values = tree.item(item)["values"]
                path = tree.item(item)["tags"][0]
                fn_title, fn_author = values[0], values[1]
                meta_title, meta_author = values[2], values[3]

                # Only add to updates if there's a mismatch or a manual edit was made
                # The user explicitly asked to "just change selected", so we apply the filename derived values
                # or manually edited values from the treeview to the PDF metadata.
                # The check below ensures we only update if the derived/edited values are different from current PDF metadata.
                if fn_title != meta_title or fn_author != meta_author:
                    updates.append((path, fn_title, fn_author))

            if not updates:
                messagebox.showinfo("No Updates", "Selected files already have matching metadata or no changes detected.")
                return

            # Show progress for updates
            progress_window = tk.Toplevel(popup)
            progress_window.title("Updating Metadata...")
            progress_window.geometry("300x100")
            progress_window.configure(bg="#333333") # Dark background
            tk.Label(progress_window, text=f"Updating {len(updates)} files...", font=('Arial', 10), bg="#333333", fg="#D3D3D3").pack(pady=20)
            progress_window.update()

            updated = self.update_pdf_metadata_batch(updates)
            progress_window.destroy()

            messagebox.showinfo("Metadata Update", f"Updated {updated} of {len(updates)} file(s).")
            self.refresh_data(popup, tree)

        # Button Frame with better layout
        btn_frame = tk.Frame(popup, bg="#333333") # Dark background
        btn_frame.pack(pady=(0, 10), fill="x", padx=10)

        # Left side buttons
        left_frame = tk.Frame(btn_frame, bg="#333333") # Dark background
        left_frame.pack(side="left")

        fix_btn = ttk.Button(left_frame, text="Fix Selected Metadata", command=fix_selected_metadata)
        fix_btn.pack(side="left", padx=(0, 5))

        # Removed "Fix All Mismatched" button as per user request
        # fix_all_btn = tk.Button(left_frame, text=f"Fix All Mismatched ({mismatch_count})",
        #                        command=fix_mismatched_metadata)
        # fix_all_btn.pack(side="left", padx=5)

        swap_btn = ttk.Button(left_frame, text="Swap Title/Author", command=swap_fn_title_author)
        swap_btn.pack(side="left", padx=5)

        # Right side buttons
        right_frame = tk.Frame(btn_frame, bg="#333333") # Dark background
        right_frame.pack(side="right")

        reload_btn = ttk.Button(right_frame, text="Select Another Folder", command=self.select_another_folder)
        reload_btn.pack(side="right", padx=(5, 0))

        close_btn = ttk.Button(right_frame, text="Exit", command=lambda: sys.exit(0))
        close_btn.pack(side="right", padx=5)

def main():
    print("Starting PDF Metadata Editor...")
    root = tk.Tk()
    root.withdraw()

    # Apply global styling for Frutiger Aero aesthetic in dark mode
    style = ttk.Style(root)
    style.theme_use('vista') # Using 'vista' theme as a base for modern look

    # Set default font for all widgets
    root.option_add("*Font", "Arial 9")

    # Define some general styles for Tkinter widgets (non-ttk) in dark mode
    root.option_add("*background", "#333333") # Dark background
    root.option_add("*Toplevel.background", "#333333") # For popup windows
    root.option_add("*Label.background", "#333333") # Dark background for labels
    root.option_add("*Label.foreground", "#D3D3D3") # Light gray text for labels


    editor = PDFMetadataEditor()
    editor.browse_folders()

    root.mainloop()

if __name__ == "__main__":
    main()
