'''Image process functions for ComfyUI nodes
by chflame https://github.com/chflame163
'''
import numpy as np
import torch
import scipy.ndimage
import cv2
from typing import Union, List
from PIL import Image, ImageFilter, ImageChops

def log(message):
    name = 'LayerStyle'
    print(f"# 😺dzNodes: {name} -> {message}")

'''Converter'''

def cv22pil(cv2_img:np.ndarray) -> Image:
    cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(cv2_img)

def pil2cv2(pil_img:Image) -> np.array:
    np_img_array = np.asarray(pil_img)
    return cv2.cvtColor(np_img_array, cv2.COLOR_RGB2BGR)

def pil2tensor(image:Image) -> torch.Tensor:
    return torch.from_numpy(np.array(image).astype(np.float32) / 255.0).unsqueeze(0)

def np2tensor(img_np: Union[np.ndarray, List[np.ndarray]]) -> torch.Tensor:
    if isinstance(img_np, list):
        return torch.cat([np2tensor(img) for img in img_np], dim=0)
    return torch.from_numpy(img_np.astype(np.float32) / 255.0).unsqueeze(0)

def tensor2np(tensor: torch.Tensor) -> List[np.ndarray]:
    if len(tensor.shape) == 3:  # Single image
        return np.clip(255.0 * tensor.cpu().numpy(), 0, 255).astype(np.uint8)
    else:  # Batch of images
        return [np.clip(255.0 * t.cpu().numpy(), 0, 255).astype(np.uint8) for t in tensor]

def tensor2pil(t_image: torch.Tensor)  -> Image:
    return Image.fromarray(np.clip(255.0 * t_image.cpu().numpy().squeeze(), 0, 255).astype(np.uint8))

def image2mask(image:Image) -> torch.Tensor:
    _image = image.convert('RGBA')
    alpha = _image.split() [0]
    bg = Image.new("L", _image.size)
    _image = Image.merge('RGBA', (bg, bg, bg, alpha))
    ret_mask = torch.tensor([pil2tensor(_image)[0, :, :, 3].tolist()])
    return ret_mask

def mask2image(mask:torch.Tensor)  -> Image:
    masks = tensor2np(mask)
    for m in masks:
        _mask = Image.fromarray(m).convert("L")
        _image = Image.new("RGBA", _mask.size, color='white')
        _image = Image.composite(
            _image, Image.new("RGBA", _mask.size, color='black'), _mask)
    return _image

'''Image Functions'''

def shift_image(image:Image, distance_x:int, distance_y:int) -> Image:
    bkcolor = (0, 0, 0)
    width = image.width
    height = image.height
    ret_image = Image.new('RGB', size=(width, height), color=bkcolor)
    for x in range(width):
        for y in range(height):
            if x > -distance_x and y > -distance_y:  # 防止回转
                if x + distance_x < width and y + distance_y < height:  # 防止越界
                    pixel = image.getpixel((x + distance_x, y + distance_y))
                    ret_image.putpixel((x, y), pixel)
    return ret_image

def chop_image(background_image:Image, layer_image:Image, blend_mode:str, opacity:int) -> Image:
    ret_image = background_image
    if blend_mode == 'normal':
        ret_image = layer_image
    if blend_mode == 'multply':
        ret_image = ImageChops.multiply(background_image,layer_image)
    if blend_mode == 'screen':
        ret_image = ImageChops.screen(background_image, layer_image)
    if blend_mode == 'add':
        ret_image = ImageChops.add(background_image, layer_image, 1, 0)
    if blend_mode == 'subtract':
        ret_image = ImageChops.subtract(background_image, layer_image, 1, 0)
    if blend_mode == 'difference':
        ret_image = ImageChops.difference(background_image, layer_image)
    if blend_mode == 'darker':
        ret_image = ImageChops.darker(background_image, layer_image)
    if blend_mode == 'lighter':
        ret_image = ImageChops.lighter(background_image, layer_image)
    # opacity
    if opacity == 0:
        ret_image = background_image
    elif opacity < 100:
        alpha = 1.0 - float(opacity) / 100
        ret_image = Image.blend(ret_image, background_image, alpha)
    return ret_image

def remove_background(image:Image, mask:Image, color:str) -> Image:
    width = image.width
    height = image.height
    ret_image = Image.new('RGB', size=(width, height), color=color)
    ret_image.paste(image, mask=mask)
    return ret_image

def motion_blur(image:Image, angle:int, blur:int) -> Image:
    angle += 45
    blur *= 5
    image = np.array(pil2cv2(image))
    M = cv2.getRotationMatrix2D((blur / 2, blur / 2), angle, 1)
    motion_blur_kernel = np.diag(np.ones(blur))
    motion_blur_kernel = cv2.warpAffine(motion_blur_kernel, M, (blur, blur))
    motion_blur_kernel = motion_blur_kernel / blur
    blurred = cv2.filter2D(image, -1, motion_blur_kernel)
    # convert to uint8
    cv2.normalize(blurred, blurred, 0, 255, cv2.NORM_MINMAX)
    blurred = np.array(blurred, dtype=np.uint8)
    ret_image = cv22pil(blurred)
    return ret_image

def direction_blur(image:Image, angle:int, blur:int, color:str) -> Image:

    ret_image = image
    return ret_image

'''Mask Functions'''

def expand_mask(mask:torch.Tensor, grow:int, blur:int) -> torch.Tensor:
    # grow
    c = 0
    kernel = np.array([[c, 1, c],
                       [1, 1, 1],
                       [c, 1, c]])
    growmask = mask.reshape((-1, mask.shape[-2], mask.shape[-1]))
    out = []
    for m in growmask:
        output = m.numpy()
        for _ in range(abs(grow)):
            if grow < 0:
                output = scipy.ndimage.grey_erosion(output, footprint=kernel)
            else:
                output = scipy.ndimage.grey_dilation(output, footprint=kernel)
        output = torch.from_numpy(output)
        out.append(output)
    # blur
    for idx, tensor in enumerate(out):
        pil_image = tensor2pil(tensor.cpu().detach())
        pil_image = pil_image.filter(ImageFilter.GaussianBlur(blur))
        out[idx] = pil2tensor(pil_image)
    ret_mask = torch.cat(out, dim=0)
    return ret_mask

def mask_invert(mask:torch.Tensor) -> torch.Tensor:
    _image = mask2image(mask)
    return image2mask(ImageChops.invert(_image))

def subtract_mask(masks_a:torch.Tensor, masks_b:torch.Tensor) -> torch.Tensor:
    return torch.clamp(masks_a - masks_b, 0, 255)

'''Color Functions'''

def RGB_to_Hex(RGB) -> str:
    color = '#'
    for i in RGB:
        num = int(i)
        color += str(hex(num))[-2:].replace('x', '0').upper()
    return color

def Hex_to_RGB(inhex) -> tuple:
    rval = inhex[1:3]
    gval = inhex[3:5]
    bval = inhex[5:]
    rgb = (int(rval, 16), int(gval, 16), int(bval, 16))
    return tuple(rgb)

'''Value Functions'''

def step_value(start_value, end_value, total_step, step) -> float:  # 按当前步数在总步数中的位置返回比例值
    factor = step / total_step
    return (end_value - start_value) * factor + start_value

def step_color(start_color, end_color, total_step, step):  # 按当前步数在总步数中的位置返回比例颜色
    if isinstance(start_color, str):
        start_color = tuple(Hex_to_RGB(start_color))
    if isinstance(end_color, str):
        end_color = tuple(Hex_to_RGB(end_color))
    start_R, start_G, start_B = start_color[0], start_color[1], start_color[2]
    end_R, end_G, end_B = end_color[0], end_color[1], end_color[2]
    ret_color = (int(step_value(start_R, end_R, total_step, step)),
                 int(step_value(start_G, end_G, total_step, step)),
                 int(step_value(start_B, end_B, total_step, step)),
                 )
    if isinstance(start_color, str):
        return RGB_to_Hex(ret_color)
    else:
        return ret_color
