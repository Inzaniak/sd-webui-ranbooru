from io import BytesIO
import random
import requests
import modules.scripts as scripts
import gradio as gr
import os
from PIL import Image

from modules import images
from modules.processing import process_images, Processed, StableDiffusionProcessingImg2Img
from modules.processing import Processed
from modules.shared import opts, cmd_opts, state, sd_model
from modules.img2img import img2img

class Booru():
    
    def __init__(self, booru, booru_url):
        self.booru = booru
        self.booru_url = booru_url
        
    def get_data(self,add_tags,max_pages=10, id=''):
        pass
    
class Gelbooru(Booru):
    
    def __init__(self):
        super().__init__('gelbooru', 'https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit=100')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return data
    
class Rule34(Booru):
    
    def __init__(self):
        super().__init__('rule34', 'https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit=100')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
class Safebooru(Booru):
    
    def __init__(self):
        super().__init__('safebooru', 'https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit=100')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['file_url'] = f"https://safebooru.org/images/{post['directory']}/{post['image']}"
        return {'post': data}

class Script(scripts.Script):  

    def title(self):

        return "Ranbooru"

    def show(self, is_img2img):

        return True
    
    def ui(self, is_img2img):
        gr.Markdown("""# Ranbooru\n## General""")
        enabled = gr.inputs.Checkbox(label="Enabled", default=True)
        booru = gr.inputs.Dropdown(["gelbooru","rule34","safebooru"], label="Booru", default="gelbooru")
        max_pages = gr.inputs.Slider(default=10, label="Max Pages", minimum=1, maximum=100, step=1)
        gr.Markdown("""## Post""")
        post_id = gr.inputs.Textbox(lines=1, label="Post ID")
        gr.Markdown("""## Tags""")
        tags = gr.inputs.Textbox(lines=1, label="Tags to Search (Pre)")
        remove_tags = gr.inputs.Textbox(lines=1, label="Tags to Remove (Post)")
        remove_bad_tags = gr.inputs.Checkbox(label="Remove bad tags", default=True)
        shuffle_tags = gr.inputs.Checkbox(label="Shuffle tags", default=True)
        change_dash = gr.inputs.Checkbox(label='Convert "_" to spaces', default=False)
        same_prompt = gr.inputs.Checkbox(label="Use same prompt for all images", default=False)
        mix_prompt = gr.inputs.Checkbox(label="Mix prompts", default=False)
        mix_amount = gr.inputs.Slider(default=2, label="Mix amount", minimum=2, maximum=10, step=1)
        change_background = gr.inputs.Radio(["Don't Change","Add Background","Remove Background"], label="Change Background", default="Don't Change")
        change_color = gr.inputs.Radio(["Don't Change","Colored","Limited Palette","Monochrome"], label="Change Color", default="Don't Change")
        gr.Markdown("""## img2img""")
        use_img2img = gr.inputs.Checkbox(label="Use img2img", default=False)
        denoising = gr.inputs.Slider(default=0.75, label="Denoising", minimum=0.05, maximum=1.0, step=0.05)
        use_last_img = gr.inputs.Checkbox(label="Use last image as img2img", default=False)
        return [enabled,tags,booru,remove_bad_tags,max_pages,change_dash,same_prompt,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount]
    
    def check_orientation(self, img):
        """Check if image is portrait, landscape or square"""
        x,y = img.size
        if x/y > 1.2:
            return [768,512]
        elif y/x > 1.2:
            return [512,768]
        else:
            return [768,768]
        

    def run(self, p, enabled, tags, booru, remove_bad_tags,max_pages,change_dash,same_prompt,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount):
        if enabled:
            # Initialize APIs
            booru_apis = {
                'gelbooru': Gelbooru(),
                'rule34': Rule34(),
                'safebooru': Safebooru()
            }
            if post_id:
                post_url = "&id="+post_id
            else:
                post_url = ""
            bad_tags = []
            if remove_bad_tags:
                bad_tags = ['watermark','text','english_text','speech_bubble','signature','artist_name','censored','bar_censor','translation','twitter_username',"twitter_logo",'patreon_username','commentary_request','tagme','commentary','character_name','mosaic_censoring','instagram_username','text_focus','english_commentary','comic','translation_request','fake_text','translated','paid_reward_available','thought_bubble','multiple_views','silent_comic','out-of-frame_censoring','symbol-only_commentary','3koma','2koma','character_watermark','spoken_question_mark','japanese_text','spanish_text','language_text','fanbox_username','commission','original','ai_generated','stable_diffusion','tagme_(artist)','text_bubble','qr_code','chinese_commentary','korean_text','partial_commentary','chinese_text','copyright_request']
            if ',' in remove_tags:
                bad_tags.extend(remove_tags.split(','))
            else:
                bad_tags.append(remove_tags)
            colored_backgrounds = ['black_background','aqua_background','white_background','colored_background','gray_background','blue_background','green_background','red_background','brown_background','purple_background','yellow_background','orange_background','pink_background','plain','transparent_background','simple_background','two-tone_background','grey_background']
            if change_background == 'Add Background':
                bad_tags.extend(colored_backgrounds)
                p.prompt = (p.prompt + ',' if p.prompt else '') + f'detailed_background,{random.choice(["outdoors","indoors"])}'
            elif change_background == 'Remove Background':
                bad_tags.extend(['outdoors','indoors'])
                p.prompt = (p.prompt + ',' if p.prompt else '') + 'plain_background,simple_background,' + random.choice(colored_backgrounds)
            if change_color == 'Colored':
                bad_tags.extend(['monochrome','greyscale','grayscale'])
            elif change_color == 'Limited Palette':
                p.prompt = (p.prompt + ',' if p.prompt else '') + '(limited_palette:1.3)'
            elif change_color == 'Monochrome':
                p.prompt = (p.prompt + ',' if p.prompt else '') + 'monochrome,greyscale,grayscale'
            add_tags = ''
            api_url = ''
            random_post = {'preview_url':''}
            prompts = []
            last_img = []
            data = {'post': [{'tags': ''}]}
            preview_urls = []
            if tags != '':
                add_tags = f'&tags=-animated+{tags.replace(",", "+")}'
            else:
                add_tags = '&tags=-animated'

            api_url = booru_apis.get(booru, Gelbooru())
            data = api_url.get_data(add_tags, max_pages, post_url)
            print(api_url.booru_url)
            random_number = random.randint(0, 99)
            if post_id:
                random_number = 0
            for _ in range(0, p.batch_size*p.n_iter):
                if same_prompt:
                    random_post = data['post'][random_number]
                else:
                    random_number = random.randint(0, 99)
                    if post_id:
                        random_number = 0
                    if mix_prompt:
                        print('mixing prompts')
                        temp_tags = []
                        max_tags = 0
                        for _ in range(0, mix_amount):
                            random_number = random.randint(0, 99)
                            if post_id:
                                random_number = 0
                            temp_tags.extend(data['post'][random_number]['tags'].split(' '))
                            max_tags = max(max_tags, len(data['post'][random_number]['tags'].split(' ')))
                        # distinct temp_tags
                        temp_tags = list(set(temp_tags))
                        random_post = data['post'][random_number]
                        print(f'Sampling {max_tags} tags')
                        if len(temp_tags) < max_tags:
                            max_tags = max(len(temp_tags), 20)
                            print(f'Using {max_tags} tags instead')
                        random_post['tags'] = ' '.join(random.sample(temp_tags, max_tags))
                    else:
                        random_post = data['post'][random_number]
                temp_tags = random_post['tags'].split(' ')
                if shuffle_tags:
                    temp_tags = random.sample(temp_tags, len(temp_tags))
                prompts.append(','.join(temp_tags))
                preview_urls.append(random_post['file_url'])
            if use_img2img:
                if use_last_img:
                    response = requests.get(random_post['file_url'])
                    last_img = [Image.open(BytesIO(response.content))]
                else:
                    for img in preview_urls:
                        response = requests.get(img)
                        last_img.append(Image.open(BytesIO(response.content)))
            new_prompts = []
            for prompt in prompts:
                new_prompt = ','.join([tag for tag in prompt.split(',') if tag.strip() not in bad_tags])     
                if change_dash:
                    new_prompt = new_prompt.replace("_", " ")
                new_prompts.append(new_prompt)
            prompts = new_prompts
            if len(prompts) == 1:
                print('Processing Single Prompt')
                if p.prompt == '':
                    p.prompt = prompts[-1]
                else:
                    p.prompt = f"{p.prompt},{prompts[-1]}"
            else:
                print('Processing Multiple Prompts')
                if p.prompt == '':
                    p.prompt = prompts
                else:
                    p.prompt = [f"{p.prompt},{prompt}" for prompt in prompts]
                p.negative_prompt = [p.negative_prompt for _ in range(0, p.batch_size*p.n_iter)]
                if use_img2img:
                    if len(last_img) < p.batch_size*p.n_iter:
                        last_img = [last_img[0] for _ in range(0, p.batch_size*p.n_iter)]
            
            if use_img2img:
                print('Using img2img')
                print('Using picture: ', random_post['file_url'])
                width, height = self.check_orientation(last_img[0])
                p2 = StableDiffusionProcessingImg2Img(
                    sd_model=sd_model,
                    outpath_samples=opts.outdir_samples or opts.outdir_img2img_samples,
                    outpath_grids=opts.outdir_grids or opts.outdir_img2img_grids,
                    prompt=p.prompt,
                    negative_prompt=p.negative_prompt,
                    seed=p.seed,
                    sampler_name='Euler a',
                    batch_size=p.batch_size,
                    n_iter=p.n_iter,
                    steps=p.steps,
                    cfg_scale=p.cfg_scale,
                    width=width,
                    height=height,
                    init_images=last_img,
                    denoising_strength=denoising,
                )
                proc = process_images(p2)
                if use_last_img:
                    proc.images.append(last_img[0])
                else:
                    for img in last_img:
                        proc.images.append(img)
            else:
                proc = process_images(p)
        else:
            proc = process_images(p)
        return proc