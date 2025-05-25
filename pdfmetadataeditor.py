import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pypdf import PdfReader, PdfWriter

def extract_metadata_from_filename(filename):
    match = re.match(r"(.+?) - (.+?)\.pdf$", filename)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""

def extract_metadata_from_pdf(path):
    try:
        reader = PdfReader(path)
        info = reader.metadata
        return (info.get("/Title", "").strip(), info.get("/Author", "").strip())
    except Exception:
        return "", ""

def update_pdf_metadata(path, title, author):
    try:
        reader = PdfReader(path)
        writer = PdfWriter()
        writer.append_pages_from_reader(reader)

        writer.add_metadata({
            "/Title": title,
            "/Author": author
        })

        temp_path = path + ".temp.pdf"
        with open(temp_path, "wb") as f:
            writer.write(f)
        
        os.replace(temp_path, path)
        return True
    except Exception as e:
        print(f"Failed to update {path}: {e}")
        return False

def collect_pdfs_recursively(folder):
    pdf_files = []
    print(f"Scanning for PDFs in: {folder}")
    for root, _, files in os.walk(folder):
        for f in files:
            if f.lower().endswith(".pdf"):
                full_path = os.path.join(root, f)
                print(f"Found PDF: {full_path}")
                fn_title, fn_author = extract_metadata_from_filename(f)
                meta_title, meta_author = extract_metadata_from_pdf(full_path)
                pdf_files.append({
                    "path": full_path,
                    "filename": f,
                    "fn_title": fn_title,
                    "fn_author": fn_author,
                    "meta_title": meta_title,
                    "meta_author": meta_author
                })
    return pdf_files

def browse_folder():
    folder = filedialog.askdirectory(title="Select Folder Containing PDFs")
    if not folder:
        return  # User cancelled

    pdf_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        messagebox.showinfo("No PDFs Found", "No PDF files were found in that folder.\nPlease select another folder.")
        browse_folder()  # 🔁 Try again
        return

    pdf_data = collect_pdfs_recursively(folder)
    show_results(pdf_data, folder)

def fix_all_metadata(tree):
    updated = 0
    for item in tree.get_children():
        values = tree.item(item)["values"]
        path = tree.item(item)["tags"][0]  # stored path as tag
        if values[0] != values[2] or values[1] != values[3]:
            success = update_pdf_metadata(path, values[0], values[1])
            if success:
                updated += 1
    messagebox.showinfo("Metadata Update Complete", f"Updated {updated} files.")

def show_results(data, folder):
    popup = tk.Toplevel()
    popup.protocol("WM_DELETE_WINDOW", lambda: sys.exit(0))
    popup.title(f"Metadata Comparison – {os.path.basename(folder)}")

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

    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    vsb.pack(side="right", fill="y")
    tree.pack(expand=True, fill="both", side="left")
    
    def swap_fn_title_author():
        for item in tree.selection():
            values = list(tree.item(item)["values"])
            values[0], values[1] = values[1], values[0]
            tree.item(item, values=values)
            
    # Insert data
    for entry in data:
        row = (entry["fn_title"], entry["fn_author"], entry["meta_title"], entry["meta_author"])
        tags = [entry["path"]]
        mismatch = row[0] != row[2] or row[1] != row[3]
        iid = tree.insert("", "end", values=row, tags=tags + (["mismatch"] if mismatch else []))
        #tree.set(iid, "selected", False)

    tree.tag_configure("mismatch", background="#ffe0e0")

    # Add editable cells
    def on_double_click(event):
        item_id = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if column not in ("#1", "#2"):  # Only fn_title and fn_author are editable
            return

        col_index = int(column[1:]) - 1
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

    # Selection logic
    selections = {}

    def toggle_selection():
        for item in tree.selection():
            path = tree.item(item)["tags"][0]
            selections[path] = True

    # Fix selected metadata
    def fix_selected_metadata():
        updated = 0
        for item in tree.get_children():
            path = tree.item(item)["tags"][0]
            if not tree.selection() or item not in tree.selection():
                continue

            values = tree.item(item)["values"]
            fn_title, fn_author = values[0], values[1]
            meta_title, meta_author = values[2], values[3]
            if fn_title != meta_title or fn_author != meta_author:
                success = update_pdf_metadata(path, fn_title, fn_author)
                if success:
                    updated += 1
        messagebox.showinfo("Metadata Update", f"Updated {updated} file(s).")
        
    def select_another():
        popup.destroy()
        browse_folder()  # Make sure browse_folder() is defined at top-level

    # Button Frame
    btn_frame = tk.Frame(popup)
    btn_frame.pack(pady=(0, 10))

    fix_btn = tk.Button(btn_frame, text="Fix Selected Metadata", command=fix_selected_metadata)
    fix_btn.pack(side="left", padx=10)
    
    swap_btn = tk.Button(btn_frame, text="Swap Filename Title/Author", command=swap_fn_title_author)
    swap_btn.pack(side="left", padx=10)

    reload_btn = tk.Button(btn_frame, text="Select Another Folder", command=select_another)
    reload_btn.pack(side="left", padx=10)

    close_btn = tk.Button(btn_frame, text="Exit", command=lambda: sys.exit(0))
    close_btn.pack(side="right", padx=10)
    

def main():
    print("Starting script...")
    root = tk.Tk()
    root.withdraw()
    browse_folder()
    root.mainloop()

if __name__ == "__main__":
    pdf_data = []
    main()
