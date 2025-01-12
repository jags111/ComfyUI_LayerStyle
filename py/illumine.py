from .imagefunc import *

class Illumine:

    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(self):
        chop_mode = ['add', 'screen', 'lighter', 'normal']
        return {
            "required": {
                "background_image": ("IMAGE", ),  #
                "layer_image": ("IMAGE",),  #
                "invert_mask": ("BOOLEAN", {"default": True}),  # 反转mask
                "blend_mode": (chop_mode,),  # 混合模式
                "opacity": ("INT", {"default": 100, "min": 0, "max": 100, "step": 1}),  # 透明度
                "iteration": ("INT", {"default": 100, "min": 0, "max": 100, "step": 1}),  # 迭代
                "glow_range": ("INT", {"default": 16, "min": -9999, "max": 9999, "step": 1}),  # 扩张
                "light_color": ("STRING", {"default": "#DFFEC2"}),  # 光源颜色
                "glow_color": ("STRING", {"default": "#F99F8E"}),  # 辉光颜色
            },
            "optional": {
                "layer_mask": ("MASK",),  #
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = 'illumine'
    CATEGORY = '😺dzNodes'
    OUTPUT_NODE = True

    def illumine(self, background_image, layer_image,
                  invert_mask, blend_mode, opacity,
                  grow, blur, glow_color,
                  layer_mask=None,
                  ):

        _canvas = tensor2pil(background_image).convert('RGB')
        _layer = tensor2pil(layer_image).convert('RGB')
        _mask = tensor2pil(layer_image).convert('RGBA').split()[-1]
        # 处理mask
        if layer_mask is not None:
            if invert_mask:
                layer_mask = 1 - layer_mask
            _mask = mask2image(layer_mask).convert('L')

        glow_mask = expand_mask(image2mask(_mask), grow, blur, 0)  #扩张，模糊
        # 合成glow
        glow_color = Image.new("RGB", _layer.size, color=glow_color)
        alpha = tensor2pil(glow_mask).convert('L')
        _glow = chop_image(tensor2pil(background_image), glow_color, blend_mode, opacity)
        _canvas.paste(_glow, mask=alpha)

        # 合成layer
        _canvas.paste(_layer, mask=_mask)
        ret_image = _canvas
        # ret_mask = glow_mask
        # return (pil2tensor(ret_image), ret_mask,)
        return (pil2tensor(ret_image),)

NODE_CLASS_MAPPINGS = {
    "LayerStyle_Illumine": Illumine
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LayerStyle_Illumine": "LayerStyle: Illumine"
}