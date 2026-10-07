"""
Image Preprocessing Module for Quantum Image Processing.

Handles loading, grayscale conversion, resizing, and normalization
of images from the NEU Surface Defect Database for quantum encoding.
"""

import numpy as np
from PIL import Image
from pathlib import Path
from typing import Tuple, Optional, Dict, Any


class ImageProcessor:
    """
    Preprocesses images for quantum image encoding (FRQI and NEQR).
    
    Handles the complete preprocessing pipeline:
    1. Load image from disk
    2. Convert to grayscale
    3. Resize to quantum-compatible resolution
    4. Normalize/quantize pixel intensities
    """

    def __init__(self, random_seed: int = 42):
        """
        Initialize the image processor.
        
        Args:
            random_seed: Seed for reproducibility where randomness is involved.
        """
        self.random_seed = random_seed
        np.random.seed(random_seed)

    def load_image(self, path: str | Path) -> np.ndarray:
        """
        Load an image from disk and convert to grayscale.
        
        Args:
            path: Path to the image file.
            
        Returns:
            2D numpy array (H, W) with uint8 values [0, 255].
            
        Raises:
            FileNotFoundError: If the image file does not exist.
            ValueError: If the image cannot be loaded.
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        try:
            img = Image.open(path).convert("L")  # Convert to grayscale
            return np.array(img, dtype=np.uint8)
        except Exception as e:
            raise ValueError(f"Failed to load image {path}: {e}")

    def resize_image(
        self, image: np.ndarray, size: Tuple[int, int]
    ) -> np.ndarray:
        """
        Resize image to a quantum-compatible resolution.
        
        Uses LANCZOS resampling for high-quality downscaling.
        
        Args:
            image: 2D numpy array (H, W) with grayscale values.
            size: Target size as (width, height). Must be powers of 2 for
                  quantum encoding (e.g., 2x2, 4x4, 8x8).
                  
        Returns:
            Resized 2D numpy array.
            
        Raises:
            ValueError: If size dimensions are not powers of 2.
        """
        w, h = size
        if not (self._is_power_of_two(w) and self._is_power_of_two(h)):
            raise ValueError(
                f"Image dimensions must be powers of 2, got {size}. "
                f"Valid sizes: (2,2), (4,4), (8,8), (16,16), ..."
            )

        img = Image.fromarray(image)
        img_resized = img.resize(size, Image.LANCZOS)
        return np.array(img_resized, dtype=np.uint8)

    def quantize_intensity(
        self, image: np.ndarray, bits: int
    ) -> np.ndarray:
        """
        Quantize pixel intensity to a specified number of bits.
        
        Reduces the intensity precision from 8-bit (256 levels) to
        the specified number of bits (2^bits levels).
        
        Args:
            image: 2D numpy array with uint8 values [0, 255].
            bits: Number of bits for intensity (e.g., 2, 4, 8).
            
        Returns:
            Quantized 2D numpy array with integer values [0, 2^bits - 1].
            
        Raises:
            ValueError: If bits is not in valid range [1, 8].
        """
        if not 1 <= bits <= 8:
            raise ValueError(f"Intensity bits must be in [1, 8], got {bits}")

        if bits == 8:
            return image.copy()

        max_val = 2**bits - 1
        # Scale from [0, 255] to [0, max_val], rounding to nearest integer
        quantized = np.round(image.astype(np.float64) / 255.0 * max_val).astype(
            np.uint8
        )
        return quantized

    def normalize_for_frqi(self, image: np.ndarray, bits: int = 8) -> np.ndarray:
        """
        Normalize pixel intensities for FRQI encoding.
        
        Maps quantized pixel values to [0, 1] range, which will then
        be converted to rotation angles θ ∈ [0, π/2].
        
        FRQI angle mapping: θ_i = normalized_intensity × π/2
        - intensity = 0 (black)  → θ = 0     → |0⟩
        - intensity = 1 (white)  → θ = π/2   → |1⟩
        
        Args:
            image: 2D numpy array with quantized integer values.
            bits: Number of intensity bits used for quantization.
            
        Returns:
            2D numpy array with float values in [0, 1].
        """
        max_val = 2**bits - 1
        if max_val == 0:
            return np.zeros_like(image, dtype=np.float64)
        return image.astype(np.float64) / max_val

    def normalize_for_neqr(self, image: np.ndarray, bits: int = 8) -> np.ndarray:
        """
        Prepare pixel intensities for NEQR encoding.
        
        Returns quantized integer values suitable for binary encoding.
        NEQR stores each pixel as a q-bit binary string.
        
        Args:
            image: 2D numpy array with quantized integer values.
            bits: Number of intensity bits.
            
        Returns:
            2D numpy array with integer values in [0, 2^bits - 1].
        """
        max_val = 2**bits - 1
        # Ensure values are within range
        return np.clip(image, 0, max_val).astype(np.uint8)

    def preprocess(
        self,
        path: str | Path,
        size: Tuple[int, int],
        bits: int = 8,
    ) -> Dict[str, Any]:
        """
        Complete preprocessing pipeline for a single image.
        
        Pipeline: Load → Grayscale → Resize → Quantize → Normalize
        
        Args:
            path: Path to the image file.
            size: Target resolution (width, height).
            bits: Intensity precision in bits.
            
        Returns:
            Dictionary containing:
                - 'original': Original grayscale image (full resolution)
                - 'resized': Resized image (uint8)
                - 'quantized': Quantized image (integer values)
                - 'frqi_normalized': Normalized for FRQI [0, 1]
                - 'neqr_values': Integer values for NEQR
                - 'pixel_matrix': 2D array of quantized values
                - 'metadata': Dict with path, size, bits, etc.
        """
        # Step 1: Load and convert to grayscale
        original = self.load_image(path)

        # Step 2: Resize to quantum-compatible resolution
        resized = self.resize_image(original, size)

        # Step 3: Quantize intensity
        quantized = self.quantize_intensity(resized, bits)

        # Step 4: Normalize for each representation
        frqi_normalized = self.normalize_for_frqi(quantized, bits)
        neqr_values = self.normalize_for_neqr(quantized, bits)

        return {
            "original": original,
            "resized": resized,
            "quantized": quantized,
            "frqi_normalized": frqi_normalized,
            "neqr_values": neqr_values,
            "pixel_matrix": quantized,
            "metadata": {
                "path": str(path),
                "filename": Path(path).name,
                "original_size": original.shape,
                "target_size": size,
                "intensity_bits": bits,
                "max_intensity": int(2**bits - 1),
                "num_pixels": size[0] * size[1],
            },
        }

    def create_synthetic_image(
        self, size: Tuple[int, int], pattern: str = "gradient", bits: int = 8
    ) -> Dict[str, np.ndarray]:
        """
        Create synthetic test images for validation.
        
        Args:
            size: Image dimensions (width, height).
            pattern: Type of pattern to generate.
                - 'gradient': Horizontal gradient from black to white
                - 'checkerboard': Alternating black and white pixels
                - 'uniform': All pixels same intensity (mid-gray)
                - 'random': Random pixel values
                - 'diagonal': Diagonal gradient
                
        Returns:
            Dictionary with 'image' (uint8), 'quantized' (int), 
            'frqi_normalized' (float), 'neqr_values' (int).
        """
        w, h = size
        max_val = 2**bits - 1

        if pattern == "gradient":
            # Horizontal gradient
            row = np.linspace(0, max_val, w, dtype=np.float64)
            image = np.tile(row, (h, 1)).astype(np.uint8)
        elif pattern == "checkerboard":
            image = np.zeros((h, w), dtype=np.uint8)
            for r in range(h):
                for c in range(w):
                    image[r, c] = max_val if (r + c) % 2 == 0 else 0
        elif pattern == "uniform":
            image = np.full((h, w), max_val // 2, dtype=np.uint8)
        elif pattern == "random":
            rng = np.random.RandomState(self.random_seed)
            image = rng.randint(0, max_val + 1, size=(h, w)).astype(np.uint8)
        elif pattern == "diagonal":
            image = np.zeros((h, w), dtype=np.uint8)
            for r in range(h):
                for c in range(w):
                    val = int((r + c) / (h + w - 2) * max_val) if (h + w - 2) > 0 else 0
                    image[r, c] = val
        else:
            raise ValueError(f"Unknown pattern: {pattern}")

        quantized = self.quantize_intensity(image, bits)
        frqi_normalized = self.normalize_for_frqi(quantized, bits)
        neqr_values = self.normalize_for_neqr(quantized, bits)

        return {
            "image": image,
            "quantized": quantized,
            "frqi_normalized": frqi_normalized,
            "neqr_values": neqr_values,
        }

    def get_pixel_info(self, image: np.ndarray, bits: int = 8) -> str:
        """
        Generate a formatted string showing pixel matrix and values.
        
        Args:
            image: 2D numpy array.
            bits: Intensity bits for context.
            
        Returns:
            Formatted string with pixel matrix.
        """
        h, w = image.shape
        max_val = 2**bits - 1
        lines = [
            f"Image size: {w}x{h} ({w * h} pixels)",
            f"Intensity range: [0, {max_val}] ({bits}-bit)",
            f"Pixel matrix:",
        ]
        for r in range(h):
            row_str = "  [" + ", ".join(f"{int(image[r, c]):3d}" for c in range(w)) + "]"
            lines.append(row_str)

        lines.append(f"\nMin: {image.min()}, Max: {image.max()}, "
                      f"Mean: {image.mean():.2f}, Std: {image.std():.2f}")
        return "\n".join(lines)

    @staticmethod
    def _is_power_of_two(n: int) -> bool:
        """Check if n is a power of 2."""
        return n > 0 and (n & (n - 1)) == 0

    def flatten_image(self, image: np.ndarray) -> np.ndarray:
        """
        Flatten 2D image to 1D array in row-major order.
        
        This is the pixel ordering used for quantum state preparation:
        position 0 = top-left, position N-1 = bottom-right.
        
        Args:
            image: 2D numpy array.
            
        Returns:
            1D numpy array of pixel values.
        """
        return image.flatten()
