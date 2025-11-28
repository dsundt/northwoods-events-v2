#!/usr/bin/env python3
"""
Gemini 3 Pro Image Generator

Generates images using Google's Gemini 3 Pro Image model via Vertex AI.

Usage:
    # As a module
    from image_generator import generate_image
    image_path = generate_image("A sunset over a lake", "output.png")
    
    # From command line
    python image_generator.py "A sunset over a lake" --output sunset.png

Environment Variables:
    GOOGLE_API_KEY - Your Google AI Studio API key
    GOOGLE_CLOUD_PROJECT - Your Google Cloud project ID (for Vertex AI)
    GOOGLE_CLOUD_REGION - Region (default: us-central1)

Setup:
    pip install google-generativeai google-cloud-aiplatform
"""

import os
import sys
import json
import base64
import argparse
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import urllib.error

# Optional imports - will use REST API if not available
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, Part
    HAS_VERTEXAI = True
except ImportError:
    HAS_VERTEXAI = False


class GeminiImageGenerator:
    """Generate images using Gemini 3 Pro Image model"""
    
    # Models to try in order of preference
    MODELS = [
        "gemini-3.0-pro-image-generation",
        "gemini-3-pro-image",
        "gemini-2.0-flash-preview-image-generation",
        "gemini-2.0-flash-exp-image-generation",
    ]
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None,
        region: str = "us-central1"
    ):
        """
        Initialize the generator.
        
        Args:
            api_key: Google API key (from AI Studio or service account)
            project_id: Google Cloud project ID (for Vertex AI)
            region: Google Cloud region (default: us-central1)
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_GEMINI_API_KEY")
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
        self.region = region or os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
        
        if not self.api_key:
            raise ValueError(
                "API key required. Set GOOGLE_API_KEY environment variable "
                "or pass api_key parameter."
            )
    
    def generate(
        self,
        prompt: str,
        output_path: Optional[str] = None,
        model: Optional[str] = None
    ) -> Tuple[Optional[bytes], str]:
        """
        Generate an image from a text prompt.
        
        Args:
            prompt: Text description of the image to generate
            output_path: Optional path to save the image
            model: Specific model to use (default: try multiple)
            
        Returns:
            Tuple of (image_bytes, model_used) or (None, error_message)
        """
        models_to_try = [model] if model else self.MODELS
        last_error = None
        
        for model_name in models_to_try:
            try:
                print(f"Trying model: {model_name}...")
                image_bytes, mime_type = self._generate_with_model(prompt, model_name)
                
                if image_bytes:
                    if output_path:
                        self._save_image(image_bytes, output_path, mime_type)
                    return image_bytes, model_name
                    
            except Exception as e:
                print(f"Model {model_name} failed: {e}")
                last_error = str(e)
                continue
        
        return None, f"All models failed. Last error: {last_error}"
    
    def _generate_with_model(self, prompt: str, model: str) -> Tuple[Optional[bytes], str]:
        """Generate image using a specific model"""
        
        # Try Vertex AI SDK first (if available and project configured)
        if HAS_VERTEXAI and self.project_id:
            try:
                return self._generate_vertexai(prompt, model)
            except Exception as e:
                print(f"Vertex AI SDK failed: {e}, trying REST API...")
        
        # Try Google Generative AI SDK (simpler setup)
        if HAS_GENAI:
            try:
                return self._generate_genai(prompt, model)
            except Exception as e:
                print(f"GenAI SDK failed: {e}, trying REST API...")
        
        # Fallback to REST API
        return self._generate_rest(prompt, model)
    
    def _generate_vertexai(self, prompt: str, model: str) -> Tuple[Optional[bytes], str]:
        """Generate using Vertex AI SDK"""
        vertexai.init(project=self.project_id, location=self.region)
        
        gen_model = GenerativeModel(model)
        response = gen_model.generate_content(
            f"Generate a high-quality image: {prompt}",
            generation_config={
                "response_modalities": ["IMAGE", "TEXT"],
                "candidate_count": 1,
            }
        )
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = base64.b64decode(part.inline_data.data)
                return image_data, part.inline_data.mime_type
        
        return None, ""
    
    def _generate_genai(self, prompt: str, model: str) -> Tuple[Optional[bytes], str]:
        """Generate using Google Generative AI SDK"""
        genai.configure(api_key=self.api_key)
        
        gen_model = genai.GenerativeModel(model)
        response = gen_model.generate_content(
            f"Generate a high-quality image: {prompt}",
            generation_config={
                "response_modalities": ["IMAGE", "TEXT"],
            }
        )
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = base64.b64decode(part.inline_data.data)
                return image_data, part.inline_data.mime_type
        
        return None, ""
    
    def _generate_rest(self, prompt: str, model: str) -> Tuple[Optional[bytes], str]:
        """Generate using REST API (no SDK required)"""
        
        # Try Vertex AI endpoint first if project is configured
        if self.project_id:
            url = (
                f"https://{self.region}-aiplatform.googleapis.com/v1/"
                f"projects/{self.project_id}/locations/{self.region}/"
                f"publishers/google/models/{model}:generateContent"
            )
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "x-goog-user-project": self.project_id,
            }
        else:
            # Use AI Studio endpoint
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
        
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": f"Generate a high-quality image: {prompt}"}]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE", "TEXT"],
                "candidateCount": 1
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
            ]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise Exception(f"HTTP {e.code}: {error_body}")
        
        # Extract image from response
        if "candidates" in data and data["candidates"]:
            parts = data["candidates"][0].get("content", {}).get("parts", [])
            for part in parts:
                if "inlineData" in part:
                    image_b64 = part["inlineData"]["data"]
                    mime_type = part["inlineData"].get("mimeType", "image/png")
                    return base64.b64decode(image_b64), mime_type
        
        return None, ""
    
    def _save_image(self, image_bytes: bytes, output_path: str, mime_type: str = "image/png"):
        """Save image bytes to file"""
        path = Path(output_path)
        
        # Determine extension from mime type if not specified
        if not path.suffix:
            ext_map = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }
            path = path.with_suffix(ext_map.get(mime_type, ".png"))
        
        path.write_bytes(image_bytes)
        print(f"Image saved to: {path}")


def generate_image(
    prompt: str,
    output_path: Optional[str] = None,
    api_key: Optional[str] = None,
    project_id: Optional[str] = None,
    model: Optional[str] = None
) -> Tuple[Optional[bytes], str]:
    """
    Convenience function to generate an image.
    
    Args:
        prompt: Text description of the image
        output_path: Optional path to save the image
        api_key: Google API key (or set GOOGLE_API_KEY env var)
        project_id: Google Cloud project ID (optional, for Vertex AI)
        model: Specific model to use (optional)
        
    Returns:
        Tuple of (image_bytes, model_used) or (None, error_message)
    """
    generator = GeminiImageGenerator(
        api_key=api_key,
        project_id=project_id
    )
    return generator.generate(prompt, output_path, model)


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description="Generate images using Google Gemini 3 Pro Image"
    )
    parser.add_argument(
        "prompt",
        help="Text description of the image to generate"
    )
    parser.add_argument(
        "-o", "--output",
        default="generated_image.png",
        help="Output file path (default: generated_image.png)"
    )
    parser.add_argument(
        "-k", "--api-key",
        help="Google API key (or set GOOGLE_API_KEY env var)"
    )
    parser.add_argument(
        "-p", "--project",
        help="Google Cloud project ID (for Vertex AI)"
    )
    parser.add_argument(
        "-m", "--model",
        help="Specific model to use"
    )
    
    args = parser.parse_args()
    
    try:
        image_bytes, result = generate_image(
            prompt=args.prompt,
            output_path=args.output,
            api_key=args.api_key,
            project_id=args.project,
            model=args.model
        )
        
        if image_bytes:
            print(f"✅ Success! Used model: {result}")
        else:
            print(f"❌ Failed: {result}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
