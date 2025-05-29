# pdfmetadataeditor

Bulk-edit PDF metadata based on file names with a fast, user-friendly GUI.

## Features

### Core Functionality
- **Recursive folder scanning** - Process PDFs in selected folders and all subfolders
- **Smart filename parsing** - Extract title and author from `Author - Title.pdf` format
- **Fallback handling** - Use full filename as title when format doesn't match
- **Metadata comparison** - Side-by-side view of filename vs. current PDF metadata
- **Interactive editing** - Double-click cells to manually edit title/author fields
- **Selective updates** - Choose which files to update with batch processing

### Performance Optimizations
- **Multithreaded processing** - Parallel PDF metadata reading for faster scanning
- **Progress tracking** - Real-time progress bars during long operations
- **Intelligent caching** - Avoid re-reading unchanged PDF files
- **Batch operations** - Efficient bulk metadata updates
- **Responsive UI** - Non-blocking interface that stays responsive during processing

### User Experience
- **Visual mismatch highlighting** - Files with different filename/metadata shown in red
- **Multiple folder support** - Process several directories in one session
- **Auto-refresh** - Automatically rescan and update display after changes
- **Title/Author swapping** - Quick button to swap title and author fields
- **Comprehensive statistics** - Shows file counts and mismatch numbers

## Usage

1. **Install dependencies:**
   ```bash
   pip install pypdf PyPDF2
   ```

2. **Run the script:**
   ```bash
   python pdfmetadataeditor.py
   ```

3. **Select folders** containing PDFs when prompted (you can add multiple folders)

4. **Review the comparison table:**
   - Red-highlighted rows show mismatched metadata
   - Double-click filename title/author cells to edit
   - Use "Swap Title/Author" for files with reversed information

5. **Apply updates:**
   - Select specific files and click "Fix Selected Metadata"
   - Or use "Fix All Mismatched" to update all problematic files at once

6. **Auto-refresh** - The table automatically updates to show your changes

## Filename Format Examples

| Filename | Parsed Author | Parsed Title |
|----------|---------------|--------------|
| `Stephen King - The Shining.pdf` | Stephen King | The Shining |
| `ComplexDocument_v2.pdf` | *(empty)* | ComplexDocument_v2 |
| `J.K. Rowling - Harry Potter.pdf` | J.K. Rowling | Harry Potter |

Files that don't match the `Author - Title.pdf` pattern will show the full filename (minus extension) as the title, allowing for manual editing.

## Requirements

- **Python 3.7+**
- **pypdf** - Modern PDF processing library
- **PyPDF2** - Additional PDF utilities
- **tkinter** - GUI framework (usually included with Python)

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
