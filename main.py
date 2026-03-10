import argparse
import torch
import logging
from src.utils.helpers import setup_logging, setup_device, visualize_output, save_model, load_model
from src.data.processing import preprocess_image, preprocess_video
from src.models.biovision_1_1s import BioVisionNetV1_1S as BioVisionNet

def main():
    # 1. Argument Parsing
    parser = argparse.ArgumentParser(description="BioVisionNet: Biologically Inspired AI")
    parser.add_argument('--input', type=str, help='Path to input image')
    parser.add_argument('--video', type=str, help='Path to input video')
    parser.add_argument('--mode', type=str, choices=['infer', 'train'], default='infer')
    parser.add_argument('--save_path', type=str, default='biovisionnet.pth')
    parser.add_argument('--load_path', type=str, default=None)
    parser.add_argument('--visualize', action='store_true', help='Save edge detection visualization')
    parser.add_argument('--temporal_backend', type=str, choices=['mean', 'lstm', 'transformer'], default='mean',
                        help='Temporal aggregation backend for sequence input')
                        help='Temporal adapter backend')
    args = parser.parse_args()

    # 2. Setup
    setup_logging()
    device = setup_device()

    # 3. Initialize Model
    model = BioVisionNet(num_classes=1000, temporal_backend=args.temporal_backend).to(device)
    
    if args.load_path:
        load_model(model, args.load_path, device)

    # 4. Inference Mode
    if args.mode == 'infer':
        model.eval()
        input_tensor = None

        if args.video:
            logging.info(f"Processing video: {args.video}")
            input_tensor = preprocess_video(args.video).to(device)
        elif args.input:
            logging.info(f"Processing image: {args.input}")
            input_tensor = preprocess_image(args.input, is_base64=False).to(device)
        else:
            logging.error("Please provide --input [image_path] or --video [video_path]")
            return

        with torch.no_grad():
            # edge_maps: [batch, seq, 32, h, w]
            # temporal_features: [batch, embed_dim]
            # logits: [batch, num_classes]
            edge_maps, features, logits = model(input_tensor)
            
            probs = torch.softmax(logits, dim=1)
            top_prob, top_class = probs.topk(1, dim=1)
            
            logging.info(f"Prediction Class: {top_class.item()}, Probability: {top_prob.item():.4f}")

            if args.visualize:
                visualize_output(edge_maps, save_path="output_vision.png")

    # 5. Training Mode (Placeholder logic)
    elif args.mode == 'train':
        logging.info("Training mode initiated... (Logic to be implemented with DataLoader)")
        model.train()
        # ... Add training loop here ...
        save_model(model, args.save_path)

if __name__ == "__main__":
    main()
