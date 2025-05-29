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
        folders = []

        while True:
            folder = filedialog.askdirectory(title="Select Folder Containing PDFs")
            if not folder:
                break

            if folder not in folders:
                folders.append(folder)

            if not messagebox.askyesno("Add Another Folder?", "Would you like to add another folder?"):
                break

        if not folders:
            return

        self.folders = folders
        self.show_progress_and_collect()

    def show_progress_and_collect(self):
        """Show progress dialog while collecting PDFs"""
        progress_window = tk.Toplevel()
        progress_window.title("Scanning PDFs...")
        progress_window.geometry("400x150")
        progress_window.transient()
        progress_window.grab_set()
        
        tk.Label(progress_window, text="Scanning folders for PDF files...").pack(pady=10)
        
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
        progress_bar.pack(pady=10, padx=20, fill="x")
        
        status_label = tk.Label(progress_window, text="Initializing...")
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
                self.show_results(pdf_data, "Multiple Folders")
            except Exception as e:
                progress_window.destroy()
                messagebox.showerror("Error", f"Error collecting PDF data: {e}")
        
        # Start collection in thread to prevent UI freezing
        thread = threading.Thread(target=collect_data, daemon=True)
        thread.start()

    def refresh_data(self, popup, tree):
        """Rescan folders and refresh the tree view"""
        # Clear cache for accurate refresh
        self.pdf_cache.clear()
        
        popup.destroy()  # Close current window
        self.show_progress_and_collect()  # Show new progress window and collect

    def show_results(self, data, folder_name):
        popup = tk.Toplevel()
        popup.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
        popup.title(f"Metadata Comparison – {folder_name} ({len(data)} files)")
        popup.geometry("1000x600")

        # Add a frame for the Treeview with scrollbars
        frame = tk.Frame(popup)
        frame.pack(expand=True, fill="both", padx=10, pady=10)

        tree = ttk.Treeview(frame, columns=("fn_title", "fn_author", "meta_title", "meta_author"),
                            show="headings", selectmode="extended")

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

        tree.tag_configure("mismatch", background="#ffe0e0")

        # Add editable cells
        def on_double_click(event):
            item_id = tree.identify_row(event.y)
            column = tree.identify_column(event.x)
            if column not in ("#1", "#2"):
                return

            x, y, width, height = tree.bbox(item_id, column)
            entry = tk.Entry(tree)
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
                
                if fn_title != meta_title or fn_author != meta_author:
                    updates.append((path, fn_title, fn_author))
            
            if not updates:
                messagebox.showinfo("No Updates", "Selected files already have matching metadata.")
                return
            
            # Show progress for updates
            progress_window = tk.Toplevel(popup)
            progress_window.title("Updating Metadata...")
            progress_window.geometry("300x100")
            tk.Label(progress_window, text=f"Updating {len(updates)} files...").pack(pady=20)
            progress_window.update()
            
            updated = self.update_pdf_metadata_batch(updates)
            progress_window.destroy()
            
            messagebox.showinfo("Metadata Update", f"Updated {updated} of {len(updates)} file(s).")
            self.refresh_data(popup, tree)
            
        def fix_mismatched_metadata():
            """Fix all files with mismatched metadata"""
            updates = []
            for item in tree.get_children():
                values = tree.item(item)["values"]
                path = tree.item(item)["tags"][0]
                if values[0] != values[2] or values[1] != values[3]:
                    updates.append((path, values[0], values[1]))
            
            if not updates:
                messagebox.showinfo("No Updates", "All files already have matching metadata.")
                return
                
            if not messagebox.askyesno("Confirm", f"Update metadata for {len(updates)} mismatched files?"):
                return
            
            progress_window = tk.Toplevel(popup)
            progress_window.title("Updating All Mismatched...")
            progress_window.geometry("300x100")
            tk.Label(progress_window, text=f"Updating {len(updates)} files...").pack(pady=20)
            progress_window.update()
            
            updated = self.update_pdf_metadata_batch(updates)
            progress_window.destroy()
            
            messagebox.showinfo("Metadata Update", f"Updated {updated} of {len(updates)} file(s).")
            self.refresh_data(popup, tree)
            
        def select_another():
            popup.destroy()
            self.browse_folders()

        # Button Frame with better layout
        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=(0, 10), fill="x", padx=10)

        # Left side buttons
        left_frame = tk.Frame(btn_frame)
        left_frame.pack(side="left")
        
        fix_btn = tk.Button(left_frame, text="Fix Selected Metadata", command=fix_selected_metadata)
        fix_btn.pack(side="left", padx=(0, 5))
        
        fix_all_btn = tk.Button(left_frame, text=f"Fix All Mismatched ({mismatch_count})", 
                               command=fix_mismatched_metadata)
        fix_all_btn.pack(side="left", padx=5)
        
        swap_btn = tk.Button(left_frame, text="Swap Title/Author", command=swap_fn_title_author)
        swap_btn.pack(side="left", padx=5)

        # Right side buttons
        right_frame = tk.Frame(btn_frame)
        right_frame.pack(side="right")
        
        reload_btn = tk.Button(right_frame, text="Select Another Folder", command=select_another)
        reload_btn.pack(side="right", padx=(5, 0))

        close_btn = tk.Button(right_frame, text="Exit", command=lambda: sys.exit(0))
        close_btn.pack(side="right", padx=5)

def main():
    print("Starting PDF Metadata Editor...")
    root = tk.Tk()
    root.withdraw()
    
    editor = PDFMetadataEditor()
    editor.browse_folders()
    
    root.mainloop()

if __name__ == "__main__":
    main()
