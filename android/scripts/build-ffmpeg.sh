#!/usr/bin/env bash
set -euo pipefail

ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$ANDROID_DIR/.build"
DOWNLOAD_DIR="$BUILD_DIR/downloads"
SOURCE_DIR="$BUILD_DIR/sources"
OUTPUT_DIR="$BUILD_DIR/ffmpeg/arm64-v8a"
PREFIX="$BUILD_DIR/prefix"
NDK_VERSION="30.0.16248370"
API_LEVEL="29"

FFMPEG_VERSION="8.1.3"
FFMPEG_SHA256="7138d28c96d9d3e3af4ee3d8cad72741f8ffb40da90c1112235dea3ecd3178a3"
LAME_VERSION="3.100"
LAME_SHA256="ddfe36cab873794038ae2c1210557ad34857a4b6bdc515785d1da9e175b1da1e"
FFMPEG_ARCHIVE="$DOWNLOAD_DIR/ffmpeg-$FFMPEG_VERSION.tar.xz"
LAME_ARCHIVE="$DOWNLOAD_DIR/lame-$LAME_VERSION.tar.gz"
FFMPEG_SOURCE="$SOURCE_DIR/ffmpeg-$FFMPEG_VERSION"
LAME_SOURCE="$SOURCE_DIR/lame-$LAME_VERSION"
OUTPUT_BINARY="$OUTPUT_DIR/libffmpeg.so"
BUILD_MARKER="$OUTPUT_DIR/build-script.sha256"
SCRIPT_HASH="$(sha256sum "$0" | cut -d' ' -f1)"

if [[ -x "$OUTPUT_BINARY" && -f "$BUILD_MARKER" && "$(cat "$BUILD_MARKER")" == "$SCRIPT_HASH" ]]; then
    printf 'Using cached FFmpeg %s / LAME %s build.\n' "$FFMPEG_VERSION" "$LAME_VERSION"
    exit 0
fi

NDK="${ANDROID_NDK_HOME:-${ANDROID_NDK_ROOT:-${ANDROID_HOME:-}/ndk/$NDK_VERSION}}"
TOOLCHAIN="$NDK/toolchains/llvm/prebuilt/linux-x86_64"
if [[ ! -x "$TOOLCHAIN/bin/aarch64-linux-android$API_LEVEL-clang" ]]; then
    printf 'Android NDK %s was not found. Set ANDROID_NDK_HOME or install it under ANDROID_HOME.\n' "$NDK_VERSION" >&2
    exit 1
fi

CC="$TOOLCHAIN/bin/aarch64-linux-android$API_LEVEL-clang"
AR="$TOOLCHAIN/bin/llvm-ar"
RANLIB="$TOOLCHAIN/bin/llvm-ranlib"
STRIP="$TOOLCHAIN/bin/llvm-strip"
NM="$TOOLCHAIN/bin/llvm-nm"

mkdir -p "$DOWNLOAD_DIR" "$SOURCE_DIR" "$OUTPUT_DIR" "$PREFIX"

download_verified() {
    local url="$1"
    local expected="$2"
    local destination="$3"
    local actual=""

    if [[ -f "$destination" ]]; then
        actual="$(sha256sum "$destination" | cut -d' ' -f1)"
    fi
    if [[ "$actual" != "$expected" ]]; then
        rm -f "$destination"
        curl --fail --location --retry 3 "$url" --output "$destination"
        actual="$(sha256sum "$destination" | cut -d' ' -f1)"
    fi
    if [[ "$actual" != "$expected" ]]; then
        printf 'SHA-256 mismatch for %s\n' "$destination" >&2
        exit 1
    fi
}

download_verified \
    "https://ffmpeg.org/releases/ffmpeg-$FFMPEG_VERSION.tar.xz" \
    "$FFMPEG_SHA256" "$FFMPEG_ARCHIVE"
download_verified \
    "https://downloads.sourceforge.net/project/lame/lame/$LAME_VERSION/lame-$LAME_VERSION.tar.gz" \
    "$LAME_SHA256" "$LAME_ARCHIVE"

if [[ ! -d "$FFMPEG_SOURCE" ]]; then
    tar -xJf "$FFMPEG_ARCHIVE" -C "$SOURCE_DIR"
fi
if [[ ! -d "$LAME_SOURCE" ]]; then
    tar -xzf "$LAME_ARCHIVE" -C "$SOURCE_DIR"
fi

export CC AR RANLIB
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="$PREFIX/lib/pkgconfig"

(
    cd "$LAME_SOURCE"
    ./configure \
        --host=aarch64-linux-android \
        --build=x86_64-linux-gnu \
        --prefix="$PREFIX" \
        --disable-shared \
        --enable-static \
        --disable-frontend \
        --disable-asm \
        --with-pic
    make -j"${BUILD_JOBS:-2}"
    make install
)

(
    cd "$FFMPEG_SOURCE"
    ./configure \
        --prefix="$PREFIX" \
        --target-os=android \
        --arch=aarch64 \
        --cpu=armv8-a \
        --enable-cross-compile \
        --sysroot="$TOOLCHAIN/sysroot" \
        --cc="$CC" \
        --ar="$AR" \
        --nm="$NM" \
        --ranlib="$RANLIB" \
        --strip="$STRIP" \
        --enable-ffmpeg \
        --disable-ffplay \
        --disable-ffprobe \
        --disable-doc \
        --disable-debug \
        --disable-network \
        --disable-autodetect \
        --disable-shared \
        --enable-static \
        --enable-pic \
        --enable-small \
        --enable-libmp3lame \
        --extra-cflags="-I$PREFIX/include" \
        --extra-ldflags="-L$PREFIX/lib" \
        --pkg-config-flags=--static
    grep -q '#define CONFIG_GPL 0' config.h
    grep -q '#define CONFIG_NONFREE 0' config.h
    make -j"${BUILD_JOBS:-2}" ffmpeg
)

cp "$FFMPEG_SOURCE/ffmpeg" "$OUTPUT_BINARY"
"$STRIP" --strip-unneeded "$OUTPUT_BINARY"
chmod 755 "$OUTPUT_BINARY"
"$TOOLCHAIN/bin/llvm-readelf" -h "$OUTPUT_BINARY" | grep -q 'AArch64'
printf '%s\n' "$SCRIPT_HASH" > "$BUILD_MARKER"
printf 'Built FFmpeg %s with LAME %s for arm64-v8a (Android API %s).\n' \
    "$FFMPEG_VERSION" "$LAME_VERSION" "$API_LEVEL"
