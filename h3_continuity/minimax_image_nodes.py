"""Official MiniMax H3 Image native workflow as one Timeline still generator."""
import folder_paths
from comfy_api.latest import io
from comfy_execution.graph_utils import GraphBuilder

StillRecipeType = io.Custom('H3C_STILL_RECIPE')
UPSTREAM = 'https://huggingface.co/Comfy-Org/MiniMax-H3-Image'
MISSING = '(none installed)'
MAX_REFERENCES = 8
COMPONENTS = {
    'diffusion_model': ('diffusion_models', 'minimax_h3_image_pruned_', 'diffusion model'),
    'text_encoder': ('text_encoders', 'qwen3vl_32b_minimax_h3_', 'text encoder'),
    'vae': ('vae', 'minimax_h3_image_vae_', 'VAE'),
}


def installed(component):
    folder, prefix, _ = COMPONENTS[component]
    return [name for name in folder_paths.get_filename_list(folder)
            if name.replace('\\', '/').rsplit('/', 1)[-1].lower().startswith(prefix)]


def choose(component, name):
    if name not in installed(component):
        folder, _, label = COMPONENTS[component]
        raise ValueError(f'MiniMax H3 Image {label} {name!r} is not installed. Select an image-model file from '
                         f'{UPSTREAM} in ComfyUI/models/{folder}. The video and P-H3 image VAEs/models are different.')
    return name


def recipe():
    return {'version': 2, 'adapter': 'pixels', 'generator': 'H3C_MiniMaxH3ImageStill', 'label': 'MiniMax H3 Image',
            'reference_limit': MAX_REFERENCES, 'reference_label': '<Picture {index}>'}


class H3C_MiniMaxH3ImageStill(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id='H3C_MiniMaxH3ImageStill', display_name='MiniMax H3 Image Still', category='H3 Continuity',
            description='Official MiniMax H3 Image, six-step native generation and reference editing. '
                        'Connect still_recipe directly to the Timeline.', enable_expand=True,
            inputs=[
                *[io.Combo.Input(component, options=installed(component) or [MISSING]) for component in COMPONENTS],
                io.String.Input('prompt', multiline=True, default=''),
                io.String.Input('instruction', multiline=True, default='', tooltip='Text added after every still prompt.'),
                io.Int.Input('seed', default=0, min=0, max=0xffffffffffffffff),
                io.Int.Input('width', default=2048, min=256, max=8192, step=32),
                io.Int.Input('height', default=2048, min=256, max=8192, step=32),
                io.Autogrow.Input('images', optional=True, template=io.Autogrow.TemplateNames(
                    io.Image.Input('image'), names=[f'image_{i}' for i in range(1, MAX_REFERENCES + 1)], min=0),
                    tooltip='image_1 is the edit base; later images supply references. The Studio fills these slots.'),
                io.Custom('LORA_STACK').Input('lora_stack', optional=True,
                    tooltip='Optional LoRA stack (for example Easy Use): filename, model strength and CLIP strength. '
                            'Applied in order to direct images and Studio stills. Use LoRAs compatible with MiniMax H3 Image.'),
            ], outputs=[io.Image.Output('image'), StillRecipeType.Output('still_recipe')])

    @classmethod
    def execute(cls, diffusion_model, text_encoder, vae, prompt, instruction, seed, width, height, images=None, lora_stack=None):
        import nodes
        if 'MiniMaxH3ImageConditioning' not in nodes.NODE_CLASS_MAPPINGS:
            raise ValueError('Update ComfyUI to a version with MiniMaxH3ImageConditioning (native MiniMax H3 Image '
                             'support added 2026-11-10), then restart ComfyUI.')
        files = {component: choose(component, name) for component, name in
                 [('diffusion_model', diffusion_model), ('text_encoder', text_encoder), ('vae', vae)]}
        for label, value in [('width', width), ('height', height)]:
            if not 256 <= value <= 8192 or value % 32:
                raise ValueError(f'MiniMax H3 Image {label} must be a multiple of 32 between 256 and 8192; got {value}.')
        if not prompt.strip():
            raise ValueError('MiniMax H3 Image needs a prompt.')
        references = {name: value for name, value in sorted((images or {}).items(),
                      key=lambda item: int(item[0].rsplit('_', 1)[-1])) if value is not None}
        if len(references) > MAX_REFERENCES:
            raise ValueError(f'MiniMax H3 Image Still supports at most {MAX_REFERENCES} references.')
        text = prompt.strip() + ('\n\n' + instruction.strip() if instruction.strip() else '')
        g = GraphBuilder()
        model = g.node('UNETLoader', unet_name=files['diffusion_model'], weight_dtype='default')
        clip = g.node('CLIPLoader', clip_name=files['text_encoder'], type='minimax', device='default')
        model_link, clip_link = model.out(0), clip.out(0)
        for lora_name, strength_model, strength_clip in lora_stack or []:
            if not lora_name or lora_name == 'None' or (strength_model == 0 and strength_clip == 0):
                continue
            lora = g.node('LoraLoader', model=model_link, clip=clip_link, lora_name=lora_name,
                          strength_model=strength_model, strength_clip=strength_clip)
            model_link, clip_link = lora.out(0), lora.out(1)
        vae_node = g.node('VAELoader', vae_name=files['vae'])
        cond = g.node('MiniMaxH3ImageConditioning', clip=clip_link, vae=vae_node.out(0), prompt=text,
                      width=width, height=height, **{'images.' + key: value for key, value in references.items()})
        negative = g.node('ConditioningZeroOut', conditioning=cond.out(0))
        sampled = g.node('KSampler', model=model_link, seed=seed, steps=6, cfg=1.0, sampler_name='euler',
                         scheduler='simple', positive=cond.out(0), negative=negative.out(0), latent_image=cond.out(1), denoise=1.0)
        decoded = g.node('VAEDecode', samples=sampled.out(0), vae=vae_node.out(0))
        return io.NodeOutput(decoded.out(0), recipe(), expand=g.finalize())
