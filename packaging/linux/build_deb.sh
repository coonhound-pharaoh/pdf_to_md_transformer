#!/usr/bin/env bash
# Build a .deb package from the PyInstaller binary (run on Linux in CI).
set -euo pipefail

VERSION="${1:-1.2.0}"
ARCH="amd64"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PKG="$ROOT/pkgroot"
BIN="$ROOT/dist/PDF-to-MD-Transformer"

rm -rf "$PKG"
mkdir -p "$PKG/DEBIAN" \
         "$PKG/usr/bin" \
         "$PKG/usr/share/applications" \
         "$PKG/usr/share/icons/hicolor/256x256/apps" \
         "$PKG/usr/share/doc/pdf-to-md-transformer"

install -m 755 "$BIN" "$PKG/usr/bin/pdf-to-md-transformer"
install -m 644 "$ROOT/assets/icon.png" "$PKG/usr/share/icons/hicolor/256x256/apps/pdf-to-md-transformer.png"
install -m 644 "$ROOT/LICENSE" "$PKG/usr/share/doc/pdf-to-md-transformer/copyright"

cat > "$PKG/usr/share/applications/pdf-to-md-transformer.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=PDF to MD Transformer
Comment=Convert PDF files to Markdown (offline, deterministic)
Exec=pdf-to-md-transformer
Icon=pdf-to-md-transformer
Terminal=false
Categories=Office;Utility;
EOF

cat > "$PKG/DEBIAN/control" <<EOF
Package: pdf-to-md-transformer
Version: $VERSION
Section: text
Priority: optional
Architecture: $ARCH
Maintainer: Michael Macauley <michael.j.macauley@gmail.com>
Recommends: tesseract-ocr, tesseract-ocr-eng
Description: Deterministic offline PDF to Markdown converter
 Converts PDF files to organized Markdown with tables and sidebars
 placed inline. Runs fully offline; document metadata is stripped.
 Scanned (image-only) pages are converted with the Tesseract OCR
 engine when tesseract-ocr is installed.
EOF

dpkg-deb --build --root-owner-group "$PKG" \
  "$ROOT/dist/pdf-to-md-transformer_${VERSION}_${ARCH}.deb"
echo "Built: $ROOT/dist/pdf-to-md-transformer_${VERSION}_${ARCH}.deb"
