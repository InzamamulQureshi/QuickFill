"""
Computer Vision Preprocessor for Quick Fill (QF).
Applies advanced OpenCV enhancement techniques to handle:
1. Blurry or low-contrast captures (Unsharp masking, Laplacian sharpening, CLAHE)
2. Skewed or tilted cards (Deskewing via minimum area rectangle / Hough transform)
3. Angled / Perspective card captures (Quadrilateral contour detection & 4-point warp)
4. Multi-orientation normalization (0°, 90°, 180°, 270°)
"""
import io
import math
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Dict, Any, Optional, List


class ImagePreprocessor:
    """Preprocesses input document images for maximum OCR accuracy on real-world ID photos."""

    @staticmethod
    def load_image(image_bytes: bytes) -> np.ndarray:
        """Decodes raw image bytes into an OpenCV BGR numpy array."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        return img

    @staticmethod
    def to_pil(cv_img: np.ndarray) -> Image.Image:
        """Converts OpenCV BGR or Grayscale image back to PIL Image."""
        if len(cv_img.shape) == 2:
            return Image.fromarray(cv_img)
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    @staticmethod
    def estimate_blur(gray: np.ndarray) -> float:
        """Calculates blurriness score using Laplacian variance (higher = sharper)."""
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @classmethod
    def sharpen_image(cls, gray: np.ndarray) -> np.ndarray:
        """
        Applies multi-stage unsharp masking and edge enhancement
        to recover text definition from slightly blurry or soft-focus images.
        """
        # 1. Unsharp Masking: (Original * 1.6) - (Gaussian Blur * 0.6)
        gaussian = cv2.GaussianBlur(gray, (0, 0), sigmaX=2.5)
        unsharp = cv2.addWeighted(gray, 1.6, gaussian, -0.6, 0)

        # 2. Gentle Laplacian high-pass sharpening kernel for character stroke definition
        kernel = np.array([
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ], dtype=np.float32)
        sharpened = cv2.filter2D(unsharp, -1, kernel)

        # 3. Clip and return
        return np.clip(sharpened, 0, 255).astype(np.uint8)

    @classmethod
    def detect_and_warp_card(cls, img: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Detects if an ID card is photographed at an angle against a surface
        and performs a 4-point perspective transform to extract a flat rectangular card.
        """
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

        img_area = h * w
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # Card should take up a reasonable portion of the frame (> 20% of image area)
            if area < img_area * 0.20:
                continue

            peri = cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, 0.025 * peri, True)

            # If quadrilateral detected
            if len(approx) == 4:
                pts = approx.reshape(4, 2)
                rect = cls._order_points(pts)

                (tl, tr, br, bl) = rect
                width_a = np.linalg.norm(br - bl)
                width_b = np.linalg.norm(tr - tl)
                max_w = max(int(width_a), int(width_b))

                height_a = np.linalg.norm(tr - br)
                height_b = np.linalg.norm(tl - bl)
                max_h = max(int(height_a), int(height_b))

                if max_w <= 0 or max_h <= 0:
                    continue

                # Standard ID card ratio is ~1.58
                aspect = max_w / float(max_h)
                if 1.1 < aspect < 2.2 or 1.1 < (1.0 / aspect) < 2.2:
                    dst = np.array([
                        [0, 0],
                        [max_w - 1, 0],
                        [max_w - 1, max_h - 1],
                        [0, max_h - 1]
                    ], dtype="float32")

                    M = cv2.getPerspectiveTransform(rect, dst)
                    warped = cv2.warpPerspective(img, M, (max_w, max_h))
                    return warped, True

        return img, False

    @staticmethod
    def _order_points(pts: np.ndarray) -> np.ndarray:
        """Orders coordinates: top-left, top-right, bottom-right, bottom-left."""
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    @classmethod
    def deskew_image(cls, gray: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detects minor rotational tilt/skew in document text lines and rotates the image
        to ensure characters and text lines are horizontally aligned.
        """
        # Threshold for dark text on light background
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Use morphological operations to group text into line segments
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        angles = []
        for c in contours:
            area = cv2.contourArea(c)
            if area < 300:
                continue
            rect = cv2.minAreaRect(c)
            w, h = rect[1]
            angle = rect[2]
            if w < h:
                angle = angle + 90
            # Keep plausible small tilt angles (-30 to +30 degrees)
            if -30 < angle < 30 and abs(angle) > 0.3:
                angles.append(angle)

        if not angles:
            return gray, 0.0

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.4:
            return gray, 0.0

        # Rotate around image center
        h, w = gray.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return rotated, median_angle

    @classmethod
    def enhance_camera_image(cls, pil_img: Image.Image) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Specialized camera capture enhancement pipeline:
        1. Rescales low-resolution webcams up to optimal neural text height (target width 1400-1800)
        2. Applies CLAHE in LAB color space to cut through specular glare and lens shadows while preserving RGB text
        3. Applies unsharp masking to recover edge crispness from soft focus or slight hand shake
        """
        img_np = np.array(pil_img)
        if len(img_np.shape) == 2:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_GRAY2BGR)
        elif img_np.shape[2] == 4:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
        else:
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

        h, w = img_bgr.shape[:2]
        meta: Dict[str, Any] = {"original_w": w, "original_h": h, "camera_upscaled": False}

        # Step 1: Detect and warp card if photographed on a background
        warped_img, rectified = cls.detect_and_warp_card(img_bgr)
        if rectified:
            img_bgr = warped_img
            h, w = img_bgr.shape[:2]
            meta["card_rectified"] = True

        # Step 2: Optimal resolution scaling (aim for width >= 1400px for sharp characters)
        if w < 1400 or h < 850:
            scale = max(1400 / w, 850 / h)
            scale = min(scale, 2.5)
            new_w = int(w * scale)
            new_h = int(h * scale)
            img_bgr = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            meta["camera_upscaled"] = True
            meta["scale_factor"] = round(scale, 2)

        # Step 3: Color-preserving contrast enhancement (LAB color space)
        lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enh = clahe.apply(l)
        enhanced_bgr = cv2.cvtColor(cv2.merge((l_enh, a, b)), cv2.COLOR_LAB2BGR)

        # Step 4: Unsharp masking for camera soft-focus
        gaussian = cv2.GaussianBlur(enhanced_bgr, (0, 0), sigmaX=2.0)
        sharpened_bgr = cv2.addWeighted(enhanced_bgr, 1.4, gaussian, -0.4, 0)
        sharpened_bgr = np.clip(sharpened_bgr, 0, 255).astype(np.uint8)

        # Convert back to PIL Image (RGB)
        pil_result = cls.to_pil(sharpened_bgr)
        return pil_result, meta

    @classmethod
    def enhance_for_ocr(cls, image_bytes: bytes) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Full robust image enhancement pipeline:
        1. Decodes image and rescales to standard OCR resolution if needed
        2. Detects perspective warp / crops card contour if visible
        3. Applies LAB color-space contrast enhancement (preserving text color definition)
        4. Applies unsharp masking for character stroke definition
        """
        img = cls.load_image(image_bytes)
        pil_img = cls.to_pil(img)
        return cls.enhance_camera_image(pil_img)

    @classmethod
    def rotate_image(cls, pil_img: Image.Image, degrees: int) -> Image.Image:
        """Rotates PIL Image by 90, 180, or 270 degrees expanding canvas."""
        return pil_img.rotate(degrees, expand=True)
