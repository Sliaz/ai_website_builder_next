import re
from playwright.sync_api import Page, expect
import imagehash
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import numpy as np
import cv2

class Playwright:
    def __init__(self, open_on: str = 'http://localhost:3000/'):
        self.open_on = open_on


    def test_has_title(self, page: Page):
        page.goto(self.open_on)

        # Expect a title "to contain" a substring.
        expect(page).to_have_title(re.compile("Playwright"))

    def test_page_exists(self, page: Page, url: str):
        page.goto(f"{self.open_on}{url}")
        expect(page).to_have_url(re.compile(url))

    def get_screenshot_of_component(self, page: Page, component_selector: str, path: str = "component.png"):
        page.locator(component_selector).screenshot(path=path)

    def phash_compare(self, page: Page, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        hash1 = imagehash.phash(Image.open("component.png"))
        hash2 = imagehash.phash(Image.open(figma_screenshot))

        return hash1 - hash2 # Lower = more similar, 0 means identical

    def ssim_compare(self, page: Page, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        component_img = Image.open("component.png")
        figma_img = Image.open(figma_screenshot)

        if component_img.size != figma_img.size:
            figma_img = figma_img.resize(component_img.size, Image.LANCZOS)

        component_array = np.array(component_img)
        figma_array = np.array(figma_img)

        score, diff = ssim(component_array, figma_array, full=True)

        diff = (diff * 255).astype(np.uint8)
        Image.fromarray(diff).save("ssim_diff.png")

        return score

    def mse_compare(self, page: Page, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        component_img = Image.open("component.png")
        figma_img = Image.open(figma_screenshot)

        if component_img.size != figma_img.size:
            figma_img = figma_img.resize(component_img.size, Image.LANCZOS)

        component_array = np.array(component_img)
        figma_array = np.array(figma_img)

        mse = np.mean((component_array.astype(float) - figma_array.astype(float)) ** 2)
        return mse

    def histogram_compare(self, page: Page, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        component_img = Image.open("component.png")
        figma_img = Image.open(figma_screenshot)

        if component_img.size != figma_img.size:
            figma_img = figma_img.resize(component_img.size, Image.LANCZOS)

        # Convert to RGB to ensure consistent comparison
        component_img = component_img.convert('RGB')
        figma_img = figma_img.convert('RGB')

        # Calculate histograms for each channel
        component_hist = [component_img.histogram()[i:i+256] for i in range(0, 768, 256)]
        figma_hist = [figma_img.histogram()[i:i+256] for i in range(0, 768, 256)]

        # Calculate correlation for each channel and average
        correlations = []
        for comp_h, fig_h in zip(component_hist, figma_hist):
            # Normalize histograms
            comp_h = np.array(comp_h, dtype=float)
            fig_h = np.array(fig_h, dtype=float)
            comp_h /= comp_h.sum()
            fig_h /= fig_h.sum()
            
            # Calculate correlation
            correlation = np.corrcoef(comp_h, fig_h)[0, 1]
            correlations.append(correlation)
        
        # Return average correlation (1.0 = identical, 0 = no correlation)
        return np.mean(correlations)

    def feature_matching(self, page: Page, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        # Load images in grayscale for feature detection
        component_img = cv2.imread("component.png", cv2.IMREAD_GRAYSCALE)
        figma_img = cv2.imread(figma_screenshot, cv2.IMREAD_GRAYSCALE)

        # Resize if needed
        if component_img.shape != figma_img.shape:
            figma_img = cv2.resize(figma_img, (component_img.shape[1], component_img.shape[0]))

        # Initialize ORB detector (fast and efficient)
        orb = cv2.ORB_create(nfeatures=1000)

        # Detect keypoints and compute descriptors
        kp1, des1 = orb.detectAndCompute(component_img, None)
        kp2, des2 = orb.detectAndCompute(figma_img, None)

        if des1 is None or des2 is None:
            return 0.0  # No features found

        # Match features using BFMatcher
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)

        # Sort matches by distance (lower is better)
        matches = sorted(matches, key=lambda x: x.distance)

        # Calculate match quality
        good_matches = [m for m in matches if m.distance < 50]  # Threshold for good matches
        
        if len(matches) == 0:
            return 0.0
        
        # Return ratio of good matches (0-1 scale)
        match_ratio = len(good_matches) / max(len(kp1), len(kp2))
        return match_ratio

    # this could be used to determine if I did import the data correctly when populating a page
    # this searches for an image inside another image

    def template_match(self, page: Page, component_selector: str, used_image: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        # Load the larger image (component) and template (used_image to find)
        component_img = cv2.imread("component.png")
        template_img = cv2.imread(used_image)

        # Convert to grayscale for better matching
        component_gray = cv2.cvtColor(component_img, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

        # Get template dimensions
        h, w = template_gray.shape

        # Perform template matching
        result = cv2.matchTemplate(component_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        
        # Get the best match location and confidence
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # max_val is the confidence (0-1, higher is better)
        # max_loc is the top-left corner of the match
        return {
            'found': max_val > 0.8,  # Threshold for considering it "found"
            'confidence': max_val,
            'location': max_loc,
            'size': (w, h)
        }

    # this seems to be using AI to compare the images

    def clip_similarity(self, page: Page, component_selector: str, figma_screenshot: str):
        # Step 1: get the component screenshot
        self.get_screenshot_of_component(page, component_selector, "component.png")

        try:
            from transformers import CLIPProcessor, CLIPModel
            import torch
            
            # Load CLIP model and processor
            model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

            # Load images
            component_img = Image.open("component.png").convert('RGB')
            figma_img = Image.open(figma_screenshot).convert('RGB')

            # Process images
            inputs = processor(images=[component_img, figma_img], return_tensors="pt", padding=True)

            # Get image embeddings
            with torch.no_grad():
                image_features = model.get_image_features(**inputs)

            # Normalize embeddings
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            # Calculate cosine similarity
            similarity = torch.nn.functional.cosine_similarity(
                image_features[0:1], 
                image_features[1:2]
            )

            return similarity.item()  # Returns value between -1 and 1 (1 = identical)
        
        except ImportError:
            raise ImportError(
                "CLIP similarity requires transformers and torch. "
                "Install with: pip install transformers torch"
            )
