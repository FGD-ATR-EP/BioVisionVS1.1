import torch
import numpy as np
from PIL import Image
import torchvision.transforms as transforms
import torchvision.io as tvio
from io import BytesIO
import base64
import logging

def preprocess_image(input_data, is_base64=True, is_url=False, target_size=(224, 224), grayscale=False):
    try:
        if is_base64:
            img_data = base64.b64decode(input_data)
            img = Image.open(BytesIO(img_data))
        elif is_url:
            import requests
            response = requests.get(input_data)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))
        else:
            img = Image.open(input_data)
        
        if grayscale:
            img = img.convert('L')
        else:
            img = img.convert('RGB')
        
        transform = transforms.Compose([
            transforms.Resize(target_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406] if not grayscale else [0.5], 
                                 std=[0.229, 0.224, 0.225] if not grayscale else [0.5])
        ])
        img_tensor = transform(img).unsqueeze(0)
        return img_tensor
    except Exception as e:
        logging.error(f"Error preprocessing image: {str(e)}")
        raise

def preprocess_video(video_path, seq_len=5, target_size=(224, 224), grayscale=False):
    try:
        video, _, _ = tvio.read_video(video_path, pts_unit='sec')
        if grayscale:
            video = video.mean(dim=-1, keepdim=True)
            
        num_frames = video.shape[0]
        if num_frames < seq_len:
             # Simple padding strategy if video is too short
             logging.warning(f"Video shorter than seq_len. Looping frames.")
             indices = np.resize(np.arange(num_frames), seq_len)
        else:
            indices = np.linspace(0, num_frames - 1, seq_len, dtype=int)
            
        frames = video[indices] # [seq_len, h, w, c]
        frames = frames.permute(0, 3, 1, 2) # [seq_len, c, h, w]
        
        transform = transforms.Compose([
            transforms.Resize(target_size),
            transforms.Normalize(mean=[0.485, 0.456, 0.406] if not grayscale else [0.5], 
                                 std=[0.229, 0.224, 0.225] if not grayscale else [0.5])
        ])
        
        frames = torch.stack([transform(frame) for frame in frames])
        return frames.unsqueeze(0) # [1, seq_len, c, h, w]
        
    except Exception as e:
        logging.error(f"Error preprocessing video: {str(e)}")
        raise
