import torch
import logging
import matplotlib.pyplot as plt
import numpy as np
import os

def setup_logging(log_file="biovisionnet.log"):
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )

def setup_device(local_rank=0):
    device = torch.device(f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu")
    logging.info(f"Using device: {device}")
    return device

def visualize_output(output, save_path='edge_output.png', index=0, frame=0):
    try:
        out = output[index, frame].detach().cpu().numpy()
        h_edges = np.mean(out[:16], axis=0)
        v_edges = np.mean(out[16:], axis=0)
        edges = np.sqrt(h_edges**2 + v_edges**2)
        
        plt.figure(figsize=(8, 8))
        plt.imshow(edges, cmap='gray')
        plt.axis('off')
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        logging.info(f"Visualization saved to {save_path}")
    except Exception as e:
        logging.error(f"Visualization failed: {e}")

def save_model(model, path):
    torch.save(model.state_dict(), path)
    logging.info(f"Model saved to {path}")

def load_model(model, path, device):
    if os.path.exists(path):
        state_dict = torch.load(path, map_location=device)
        model.load_state_dict(state_dict)
        logging.info(f"Model loaded from {path}")
    else:
        logging.warning(f"Model file not found at {path}")
