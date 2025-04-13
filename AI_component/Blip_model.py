import torch
from transformers import AutoProcessor, BlipForConditionalGeneration
from transformers import BlipProcessor

checkpoint_path = "best_model.pth"

processor = AutoProcessor.from_pretrained("Ornelas/blip_finetuned_fashion")
model = BlipForConditionalGeneration.from_pretrained("Ornelas/blip_finetuned_fashion")
device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

# Nạp checkpoint, giả sử checkpoint chỉ chứa các trọng số của model
checkpoint = torch.load(checkpoint_path, map_location=device)

# Kiểm tra nếu checkpoint có key 'model_state_dict', nạp trọng số từ đó
if 'model_state_dict' in checkpoint:
    model.load_state_dict(checkpoint['model_state_dict'])
else:
    model.load_state_dict(checkpoint)

# Chuyển model sang chế độ eval để dùng cho inference
model.eval()

print("Checkpoint loaded successfully!")


def load_blip_model(image):
    inputs = processor(images=image, return_tensors="pt").to(device)
    pixel_values = inputs.pixel_values
    # Generate captions
    generated_ids = model.generate(pixel_values=pixel_values, max_length=50)
    generated_caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return generated_caption