# pdfmetadataeditor

A utility for bulk-editing PDF metadata using filenames.

## Features

### Core Functionality
- **Recursive Folder Scanning:** Processes PDF files within selected directories and their subfolders.
- **Filename Parsing:** Extracts title and author from `Author - Title.pdf` filename format.
- **Fallback Naming:** Uses the full filename as the title if it doesn't match the standard format.
- **Metadata Comparison:** Displays a side-by-side view of filename-derived information versus existing PDF metadata.
- **Interactive Editing:** Allows manual modification of title and author fields directly in the interface.
- **Selective Updates:** Provides options to update metadata for specific, chosen files in a batch.

### Performance Optimizations
- **Multithreaded Processing:** Utilizes parallel operations for faster PDF metadata reading.
- **Progress Tracking:** Shows real-time progress during operations.
- **Intelligent Caching:** Avoids redundant PDF file reads for unchanged files.
- **Batch Operations:** Efficiently updates metadata for multiple files.
- **Responsive Interface:** The application remains usable during processing tasks.

### User Experience
- **Mismatch Identification:** Clearly highlights files where filename information differs from embedded metadata.
- **Multiple Folder Processing:** Supports processing PDFs from several directories in one session.
- **Automatic Refresh:** The display updates automatically after changes are applied.
- **Title/Author Swap:** Includes a quick option to interchange title and author fields.
- **Summary Statistics:** Displays total file counts and the number of mismatched entries.

## Usage

1.  **Install dependencies:**
    ```bash
    pip install pypdf PyPDF2
    ```

2.  **Run the script:**
    ```bash
    python pdfmetadataeditor.py
    ```

3.  **Select folders** containing PDFs when prompted (you can add multiple folders).

4.  **Review the comparison table:**
    * Rows with mismatched metadata are highlighted.
    * Double-click filename title/author cells to edit.
    * Use "Swap Title/Author" for files with reversed information.

5.  **Apply updates:**
    * Select specific files and click "Fix Selected Metadata."
    * Alternatively, use "Fix All Mismatched" to update all identified problematic files.

6.  **Automatic Updates:** The table automatically updates to show your changes.

## Filename Format Examples

| Filename | Parsed Author | Parsed Title |
|----------|---------------|--------------|
| `Stephen King - The Shining.pdf` | Stephen King | The Shining |
| `ComplexDocument_v2.pdf` | *(empty)* | ComplexDocument_v2 |
| `J.K. Rowling - Harry Potter.pdf` | J.K. Rowling | Harry Potter |

Files that do not match the `Author - Title.pdf` pattern will use the full filename (excluding the extension) as the title, which can then be manually edited.

## Requirements

-   **Python 3.7+**
-   **pypdf** - For modern PDF processing.
-   **PyPDF2** - For additional PDF utilities.
-   **tkinter** - Python's standard GUI framework (typically included with Python).

## Installation

```bash
pip install pypdf PyPDF2
```

## Performance Notes

The tool uses multithreaded processing to handle large collections efficiently:
- **Small collections** (< 50 files): <1 minute
- **Medium collections** (50-200 files): 1-5 minutes 
- **Large collections** (200+ files): 5+ minutes minutes (not recommended)

Processing speed depends primarily on PDF file complexity and disk I/O performance. If you run into pdf errors you may have to fix them with [ghost](https://ghostscript.com/)

## License

MIT License - Feel free to modify and distribute.****
