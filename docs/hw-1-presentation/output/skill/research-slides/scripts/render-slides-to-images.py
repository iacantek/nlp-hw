#!/usr/bin/env python3
"""
render-slides-to-images.py

Converts a PowerPoint (.pptx) presentation into per-slide PNG images for visual
inspection, and prints a speaker-notes word count and 7-minute timing report.

Supports rendering all slides or only specific changed slides (--slides 2,5,10).
Uses Microsoft PowerPoint + macOS PDFKit/Quartz when available for exact native
rendering, with a pure-Python PIL fallback if PowerPoint is unavailable.

Usage:
  python3 render-slides-to-images.py --pptx <deck.pptx> --out-dir <dir> [--slides 1,3,5] [--scale 2.5]
"""

import argparse
import os
import subprocess
import sys
import tempfile
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN


SWIFT_PDF_RENDERER = r"""
import Foundation
import PDFKit
import AppKit

let args = CommandLine.arguments
guard args.count >= 5 else {
    fputs("Usage: render_pdf <pdf_path> <page_1_indexed> <scale> <out_png>\n", stderr)
    exit(1)
}
let pdfPath = args[1]
let pageIndex = Int(args[2])! - 1
let scale = CGFloat(Double(args[3])!)
let outPath = args[4]

guard let doc = PDFDocument(url: URL(fileURLWithPath: pdfPath)),
      let page = doc.page(at: pageIndex) else {
    fputs("Failed to open PDF or page\n", stderr)
    exit(2)
}

let rect = page.bounds(for: .mediaBox)
let width = Int(rect.width * scale)
let height = Int(rect.height * scale)

let rep = NSBitmapImageRep(
    bitmapDataPlanes: nil,
    pixelsWide: width,
    pixelsHigh: height,
    bitsPerSample: 8,
    samplesPerPixel: 4,
    hasAlpha: true,
    isPlanar: false,
    colorSpaceName: .deviceRGB,
    bytesPerRow: 0,
    bitsPerPixel: 0
)!

NSGraphicsContext.saveGraphicsState()
NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
if let cg = NSGraphicsContext.current?.cgContext {
    cg.setFillColor(NSColor.white.cgColor)
    cg.fill(CGRect(x: 0, y: 0, width: CGFloat(width), height: CGFloat(height)))
    cg.scaleBy(x: scale, y: scale)
    page.draw(with: .mediaBox, to: cg)
}
NSGraphicsContext.restoreGraphicsState()

if let data = rep.representation(using: .png, properties: [:]) {
    try! data.write(to: URL(fileURLWithPath: outPath))
}
"""


def parse_slide_list(slides_arg, total_slides):
    if not slides_arg:
        return list(range(1, total_slides + 1))
    selected = []
    for part in slides_arg.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            for i in range(int(start_s), int(end_s) + 1):
                if 1 <= i <= total_slides and i not in selected:
                    selected.append(i)
        else:
            i = int(part)
            if 1 <= i <= total_slides and i not in selected:
                selected.append(i)
    return selected


def try_powerpoint_pdf_render(pptx_path, out_dir, slide_indices, scale=2.5):
    """Exports PPTX to PDF via Microsoft PowerPoint AppleScript and renders requested pages."""
    abs_pptx = os.path.abspath(pptx_path)
    abs_out = os.path.abspath(out_dir)
    os.makedirs(abs_out, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "deck.pdf")
        applescript = f'''
        tell application "Microsoft PowerPoint"
            open POSIX file "{abs_pptx}"
            save active presentation in POSIX file "{pdf_path}" as save as PDF
            close active presentation saving no
        end tell
        '''
        res = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True)
        if res.returncode != 0 or not os.path.exists(pdf_path):
            return False

        swift_src = os.path.join(tmpdir, "render_pdf.swift")
        swift_bin = os.path.join(tmpdir, "render_pdf")
        with open(swift_src, "w", encoding="utf-8") as f:
            f.write(SWIFT_PDF_RENDERER)

        comp = subprocess.run(["swiftc", "-O", swift_src, "-o", swift_bin], capture_output=True, text=True)
        if comp.returncode != 0:
            return False

        for idx in slide_indices:
            out_png = os.path.join(abs_out, f"slide_{idx}.png")
            r = subprocess.run([swift_bin, pdf_path, str(idx), str(scale), out_png], capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(out_png):
                return False
            print(f"[Native PDF Render] Slide {idx} -> {out_png}")
    return True


def fallback_pil_render(pptx_path, out_dir, slide_indices, dpi=150):
    """Pure-Python PIL fallback renderer if Microsoft PowerPoint is unavailable."""
    os.makedirs(out_dir, exist_ok=True)
    prs = Presentation(pptx_path)
    sw_in = prs.slide_width.inches
    sh_in = prs.slide_height.inches
    W = int(round(sw_in * dpi))
    H = int(round(sh_in * dpi))
    pt_scale = dpi / 72.0

    for idx in slide_indices:
        slide = prs.slides[idx - 1]
        canvas = Image.new("RGB", (W, H), (255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        for shape in slide.shapes:
            x = int(round(shape.left.inches * dpi))
            y = int(round(shape.top.inches * dpi))
            w = int(round(shape.width.inches * dpi))
            h = int(round(shape.height.inches * dpi))
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                im = Image.open(BytesIO(shape.image.blob)).convert("RGBA")
                im = im.resize((max(1, w), max(1, h)), Image.Resampling.LANCZOS)
                canvas.paste(im, (x, y), im)
                continue
            draw.rectangle([x, y, x + w, y + h], outline=(203, 213, 225), width=max(1, int(pt_scale)))
            if shape.has_text_frame and shape.text_frame.text.strip():
                draw.text((x + 8, y + 6), shape.text_frame.text.strip()[:140], fill=(15, 23, 42))
        out_png = os.path.join(out_dir, f"slide_{idx}.png")
        canvas.save(out_png)
        print(f"[Fallback Render] Slide {idx} -> {out_png}")


def print_timing_report(pptx_path, wpm=135.0):
    prs = Presentation(pptx_path)
    print("\n=== Speaker Notes & 7-Minute Pacing Check ===")
    total_main_words = 0
    total_all_words = 0
    for idx, slide in enumerate(prs.slides, 1):
        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        words = len(notes.split()) if notes else 0
        sentences = [s.strip() for s in notes.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        sec = int(round((words / wpm) * 60.0))
        is_backup = any("[Backup]" in sh.text_frame.text for sh in slide.shapes if sh.has_text_frame)
        tag = " [Backup]" if is_backup else ""
        status = "OK (<60s)" if sec < 60 else "OVER 60s!"
        print(f"Slide {idx:2d}{tag}: {len(sentences)} sentences | {words:3d} words | ~{sec:2d}s | {status}")
        total_all_words += words
        if not is_backup:
            total_main_words += words

    main_sec = int(round((total_main_words / wpm) * 60.0))
    all_sec = int(round((total_all_words / wpm) * 60.0))
    print(f"---------------------------------------------")
    print(f"Main Talk Total : {total_main_words} words (~{main_sec // 60}m {main_sec % 60:02d}s at {int(wpm)} wpm)")
    print(f"With Backup     : {total_all_words} words (~{all_sec // 60}m {all_sec % 60:02d}s at {int(wpm)} wpm)")


def main():
    parser = argparse.ArgumentParser(description="Render PPTX slides to PNG images and verify talk timing.")
    parser.add_argument("--pptx", required=True, help="Path to input .pptx file")
    parser.add_argument("--out-dir", required=True, help="Directory to save rendered slide_N.png files")
    parser.add_argument("--slides", default="", help="Comma-separated 1-indexed slide numbers (e.g., '1,3,5-7'). Default: all.")
    parser.add_argument("--scale", type=float, default=2.5, help="Render scale factor for PDF rasterization (default: 2.5)")
    args = parser.parse_args()

    prs = Presentation(args.pptx)
    slide_indices = parse_slide_list(args.slides, len(prs.slides))

    ok = try_powerpoint_pdf_render(args.pptx, args.out_dir, slide_indices, scale=args.scale)
    if not ok:
        fallback_pil_render(args.pptx, args.out_dir, slide_indices)

    print_timing_report(args.pptx)


if __name__ == "__main__":
    main()
