# AI Copilot Instructions for Vietnam License Plate Detection

## Project Overview
Vietnamese license plate detection and OCR system using YOLO for plate localization and EasyOCR for text recognition. The pipeline detects plates in vehicle images, extracts text, and validates/corrects OCR output against Vietnamese plate format rules.

## Architecture

### Core Pipeline (detect.ipynb)
1. **YOLO Detection**: Locates license plate bounding boxes in images using `license_plate_best.pt` model
2. **Plate Extraction**: Crops detected plate region from original image
3. **Preprocessing**: Gray conversion → bilateral filtering → OTSU threshold → 2x upscaling for OCR accuracy
4. **Deskewing** (via rotated.py): Detects and corrects rotated plates using Hough line detection
5. **OCR**: EasyOCR reads plate text, filtered to [A-Z0-9] characters only
6. **Format Validation**: Applies Vietnamese plate format rules (8 chars: digits-digits-letter-digits-digits-digits-digits-digits)

### Key Components
- **rotated.py**: `deskew_plate()` function using HoughLines to detect plate rotation angle via median of detected lines
- **detect.ipynb**: Main pipeline with `correct_plate_format()` for OCR error correction and `debug_plate_pipeline()` for visualization
- **Models**: Located in `license_plate/` directory; use `license_plate_best.pt` (preferred over `license_plate_last.pt`)

## Vietnamese Plate Format Rules
Format: `NNALNNNN` (N=digit, A=letter, exactly 8 chars)

### OCR Error Correction Mapping
- Digits commonly misread as letters: `0→O, 1→I, 5→S, 8→B, 6→G, 2→Z`
- Letters commonly misread as digits: `O→0, I→1, Z→2, S→5, B→8, G→6, T→7`
- Positions 0-1, 3-7 must be digits; position 2 must be a letter
- Invalid plates after correction are rejected (empty string returned)

## Dependencies & GPU
- **YOLO**: `ultralytics` (requires `license_plate_best.pt`)
- **OCR**: `easyocr` with GPU enabled (`gpu=True`) - verify with `torch.cuda.is_available()`
- **Vision**: OpenCV (`cv2`)
- Image preprocessing uses bilateral filter (noise reduction) + OTSU thresholding before OCR

## Important Patterns
- Always use `model(img, verbose=False)` to suppress YOLO output during batch processing
- Crop images with bounds clamping: `max(0, x1)` and `min(w, x2)` to prevent out-of-bounds errors
- EasyOCR reader initialized once (cell 2) and reused to avoid repeated GPU loading
- `readtext()` called with `detail=0` to return only text, not confidence scores

## Debugging & Testing
- Use `debug_plate_pipeline()` for step-by-step visualization (6 subplot grid showing original → YOLO → crop → gray → threshold → deskewed)
- Test images located in `data/images/` directory
- Check GPU availability before running: `print(torch.cuda.is_available())`
