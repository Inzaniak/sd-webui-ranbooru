from io import BytesIO
import random
import requests
import modules.scripts as scripts
import gradio as gr
import os
from PIL import Image
import numpy as np

from modules import images
from modules.processing import process_images, StableDiffusionProcessingImg2Img
from modules import shared
from modules.img2img import img2img
from modules.sd_hijack import model_hijack

COLORED_BG = ['black_background','aqua_background','white_background','colored_background','gray_background','blue_background','green_background','red_background','brown_background','purple_background','yellow_background','orange_background','pink_background','plain','transparent_background','simple_background','two-tone_background','grey_background']
ADD_BG = ['outdoors','indoors']
BW_BG = ['monochrome','greyscale','grayscale']
POST_AMOUNT = 100
DEBUG = False
RATING_TYPES = {
    "none": {
        "All": "All"
    },
    "full": {
        "All": "All",
        "Safe": "safe",
        "Questionable": "questionable",
        "Explicit": "explicit"
    },
    "single": {
        "All": "All",
        "Safe": "g",
        "Sensitive": "s",
        "Questionable": "q",
        "Explicit": "e"
    }
}
RATINGS = {
    "e621": RATING_TYPES['full'],
    "danbooru": RATING_TYPES['single'],
    "aibooru": RATING_TYPES['full'],
    "yande.re": RATING_TYPES['full'],
    "konachan": RATING_TYPES['full'],
    "safebooru": RATING_TYPES['none'],
    "rule34": RATING_TYPES['full'],
    "xbooru": RATING_TYPES['full'],
    "gelbooru": RATING_TYPES['single']
}

def get_available_ratings(booru):
    mature_ratings =  gr.Radio.update(choices=RATINGS[booru].keys(), value="All")
    return mature_ratings

def check_exception(booru, parameters):
    post_id = parameters.get('post_id')
    tags = parameters.get('tags')
    if booru == 'konachan' and post_id:
        raise Exception("Konachan does not support post IDs")
    if booru == 'yande.re' and post_id:
        raise Exception("Yande.re does not support post IDs")
    if booru == 'e621' and post_id:
        raise Exception("e621 does not support post IDs")
    if booru == 'danbooru' and len(tags.split(',')) > 1:
        raise Exception("Danbooru does not support multiple tags. You can have only one tag.")

class Booru():
    
    def __init__(self, booru, booru_url):
        self.booru = booru
        self.booru_url = booru_url
        self.headers = {'user-agent': 'my-app/0.0.1'}
        
    def get_data(self,add_tags,max_pages=10, id=''):
        pass
    
class Gelbooru(Booru):
    
    def __init__(self):
        super().__init__('gelbooru', f'https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return data
    
class XBooru(Booru):
    
    def __init__(self):
        super().__init__('xbooru', f'https://xbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['file_url'] = f"https://xbooru.com/images/{post['directory']}/{post['image']}"
        return {'post': data}
    
class Rule34(Booru):
    
    def __init__(self):
        super().__init__('rule34', f'https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
class Safebooru(Booru):
    
    def __init__(self):
        super().__init__('safebooru', f'https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&pid={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['file_url'] = f"https://safebooru.org/images/{post['directory']}/{post['image']}"
        return {'post': data}
    
class Konachan(Booru):
    
    def __init__(self):
        super().__init__('konachan', f'https://konachan.com/post.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
class Yandere(Booru):
    
    def __init__(self):
        super().__init__('yande.re', f'https://yande.re/post.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        return {'post': data}
    
class AIBooru(Booru):
    
    def __init__(self):
        super().__init__('AIBooru', f'https://aibooru.online/posts.json?limit={POST_AMOUNT}')
                
    def get_data(self, add_tags, max_pages=10,id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url)
        data = res.json()
        for post in data:
            post['tags'] = post['tag_string']
        return {'post': data}
    
class Danbooru(Booru):
    
    def __init__(self):
        super().__init__('danbooru', f'https://danbooru.donmai.us/posts.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url, headers=self.headers)
        data = res.json()
        for post in data:
            post['tags'] = post['tag_string']
        return {'post': data}
    
class e621(Booru):
    
    def __init__(self):
        super().__init__('danbooru', f'https://e621.net/posts.json?limit={POST_AMOUNT}')
        
    def get_data(self, add_tags, max_pages=10, id=''):
        if id:
            add_tags = ''
        self.booru_url = f"{self.booru_url}&page={random.randint(0,max_pages)}{id}{add_tags}"
        res = requests.get(self.booru_url, headers=self.headers)
        data = res.json()['posts']
        for post in data:
            temp_tags = []
            sublevels = ['general','artist','copyright','character','species']
            for sublevel in sublevels:
                temp_tags.extend(post['tags'][sublevel])
            post['tags'] = ' '.join(temp_tags)
            post['score'] = post['score']['total']
        return {'post': data}
    
def generate_chaos(pos_tags,neg_tags,chaos_amount):
    # create a list with the tags in the prompt and in the negative prompt
    chaos_list = [tag for tag in pos_tags.split(',') + neg_tags.split(',') if tag.strip() != '']
    # distinct the list
    chaos_list = list(set(chaos_list))
    random.shuffle(chaos_list)
    # put 50% of the tags in the prompt and the remaining 50% in the negative prompt
    len_list = round(len(chaos_list)*chaos_amount)
    pos_list = chaos_list[len_list:]
    pos_prompt = ','.join(pos_list)
    neg_list = chaos_list[:len_list]
    random.shuffle(neg_list)
    neg_prompt = ','.join(neg_list)
    return pos_prompt, neg_prompt

class Script(scripts.Script):   
    
    def __init__(self):
        self.previous_loras = ''
        self.last_img = []
        self.real_steps = 0
        
    def hide_object(self, obj, booru):
        print(f'hide_object: {obj}, {booru.value}')
        if booru.value == 'konachan' or booru.value == 'yande.re':
            obj.interactive = False
        else:
            obj.interactive = True

    def title(self):

        return "Ranbooru"

    def show(self, is_img2img):

        return scripts.AlwaysVisible
    
    def ui(self, is_img2img):
        with gr.Group():
            with gr.Accordion("Ranbooru", open = False):
                enabled = gr.Checkbox(label="Enable")
                booru = gr.Dropdown(["gelbooru","rule34","safebooru","danbooru","konachan",'yande.re','aibooru','xbooru','e621'], label="Booru", value="gelbooru")
                max_pages = gr.Slider(label="Max Pages", minimum=1, maximum=100,value=100, step=1)
                gr.Markdown("""## Post""")
                post_id = gr.Textbox(lines=1, label="Post ID")
                gr.Markdown("""## Tags""")
                tags = gr.Textbox(lines=1, label="Tags to Search (Pre)")
                remove_tags = gr.Textbox(lines=1, label="Tags to Remove (Post)")
                mature_rating = gr.Radio(RATINGS['gelbooru'].keys(), label="Mature Rating", value="All")
                remove_bad_tags = gr.Checkbox(label="Remove bad tags", value=True)
                shuffle_tags = gr.Checkbox(label="Shuffle tags", value=True)
                change_dash = gr.Checkbox(label='Convert "_" to spaces', value=False)
                same_prompt = gr.Checkbox(label="Use same prompt for all images", value=False)
                limit_tags = gr.Slider(value=1.0, label="Limit tags", minimum=0.05, maximum=1.0, step=0.05)
                max_tags = gr.Slider(value=100, label="Max tags", minimum=1, maximum=100, step=1)
                change_background = gr.Radio(["Don't Change","Add Background","Remove Background","Remove All"], label="Change Background", value="Don't Change")
                change_color = gr.Radio(["Don't Change","Colored","Limited Palette","Monochrome"], label="Change Color", value="Don't Change")
                sorting_order = gr.Radio(["Random","High Score","Low Score"], label="Sorting Order", value="Random")
                
                booru.change(get_available_ratings, booru, mature_rating) # update available ratings
                
                gr.Markdown("""\n---\n""")
                with gr.Group():
                    with gr.Accordion("Img2Img", open = False):
                        use_img2img = gr.Checkbox(label="Use img2img", value=False)
                        denoising = gr.Slider(value=0.75, label="Denoising", minimum=0.05, maximum=1.0, step=0.05)
                        use_last_img = gr.Checkbox(label="Use last image as img2img", value=False)
                with gr.Group():
                    with gr.Accordion("Extra", open = False):
                        with gr.Box():
                            mix_prompt = gr.Checkbox(label="Mix prompts", value=False)
                            mix_amount = gr.Slider(value=2, label="Mix amount", minimum=2, maximum=10, step=1)
                        with gr.Box():
                            chaos_mode = gr.Radio(["None","Chaos","Less Chaos"], label="Chaos Mode", value="None")
                            chaos_amount = gr.Slider(value=0.5, label="Chaos Amount %", minimum=0.1, maximum=1, step=0.05)
                        with gr.Box():
                            negative_mode = gr.Radio(["None","Negative"], label="Negative Mode", value="None")
        with gr.Group():
            with gr.Accordion("LoRAnado", open = False):
                with gr.Box():
                    lora_enabled = gr.Checkbox(label="Use LoRAnado", value=False)
                    lora_lock_prev = gr.Checkbox(label="Lock previous LoRAs", value=False)
                    lora_folder = gr.Textbox(lines=1, label="LoRAs Subfolder")
                    lora_amount = gr.Slider(default=1, label="LoRAs Amount", minimum=1, maximum=10, step=1)
                with gr.Box():
                    lora_min = gr.Slider(value=-1.0, label="Min LoRAs Weight", minimum=-1.0, maximum=1, step=0.1)
                    lora_max = gr.Slider(value=1.0, label="Max LoRAs Weight", minimum=-1.0, maximum=1.0, step=0.1)
                    lora_custom_weights = gr.Textbox(lines=1, label="LoRAs Custom Weights")
        return [enabled,tags,booru,remove_bad_tags,max_pages,change_dash,same_prompt,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount,chaos_mode,negative_mode,chaos_amount,limit_tags,max_tags,sorting_order,mature_rating,lora_folder,lora_amount,lora_min,lora_max,lora_enabled,lora_custom_weights,lora_lock_prev]
                    
    def check_orientation(self, img):
        """Check if image is portrait, landscape or square"""
        x,y = img.size
        if x/y > 1.2:
            return [768,512]
        elif y/x > 1.2:
            return [512,768]
        else:
            return [768,768]
        
    def loranado(self,lora_enabled,lora_folder,lora_amount,lora_min,lora_max,lora_custom_weights,p,lora_lock_prev):
        lora_prompt = ''
        if lora_enabled:
            if lora_lock_prev:
                lora_prompt = self.previous_loras
            else:
                loras = []
                loras = os.listdir(f'{lora_folder}')
                # get only .safetensors files
                loras = [lora.replace('.safetensors','') for lora in loras if lora.endswith('.safetensors')]                
                for l in range(0, lora_amount):
                    lora_weight = 0
                    if lora_custom_weights != '':
                        lora_weight = float(lora_custom_weights.split(',')[l])
                    while lora_weight == 0:
                        lora_weight = round(random.uniform(lora_min, lora_max), 1)
                    lora_prompt += f'<lora:{random.choice(loras)}:{lora_weight}>'
                    self.previous_loras = lora_prompt
        if lora_prompt:
            if type(p.prompt) == list:
                for num, pr in enumerate(p.prompt):
                    p.prompt[num] = f'{lora_prompt} {pr}'
            else:
                pass
        return p

    def before_process(self, p, enabled, tags, booru, remove_bad_tags,max_pages,change_dash,same_prompt,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount,chaos_mode,negative_mode,chaos_amount,limit_tags,max_tags,sorting_order,mature_rating,lora_folder,lora_amount,lora_min,lora_max,lora_enabled,lora_custom_weights,lora_lock_prev):
        if enabled:
            # Initialize APIs
            booru_apis = {
                'gelbooru': Gelbooru(),
                'rule34': Rule34(),
                'safebooru': Safebooru(),
                'danbooru': Danbooru(),
                'konachan': Konachan(),
                'yande.re': Yandere(),
                'aibooru': AIBooru(),
                'xbooru': XBooru(),
                'e621': e621(),
            }
            original_prompt = p.prompt
            # Check if compatible
            check_exception(booru, {'tags':tags,'post_id':post_id})
            
            # Manage Post ID
            if post_id:
                post_url = "&id="+post_id
            else:
                post_url = ""
                
            # Manage Bad Tags
            bad_tags = []
            if remove_bad_tags:
                bad_tags = ['mixed-language_text','watermark','text','english_text','speech_bubble','signature','artist_name','censored','bar_censor','translation','twitter_username',"twitter_logo",'patreon_username','commentary_request','tagme','commentary','character_name','mosaic_censoring','instagram_username','text_focus','english_commentary','comic','translation_request','fake_text','translated','paid_reward_available','thought_bubble','multiple_views','silent_comic','out-of-frame_censoring','symbol-only_commentary','3koma','2koma','character_watermark','spoken_question_mark','japanese_text','spanish_text','language_text','fanbox_username','commission','original','ai_generated','stable_diffusion','tagme_(artist)','text_bubble','qr_code','chinese_commentary','korean_text','partial_commentary','chinese_text','copyright_request','heart_censor','censored_nipples']
            if ',' in remove_tags:
                bad_tags.extend(remove_tags.split(','))
            else:
                bad_tags.append(remove_tags)
                
            # Manage Backgrounds
            if change_background == 'Add Background':
                bad_tags.extend(COLORED_BG)
                p.prompt = (p.prompt + ',' if p.prompt else '') + f'detailed_background,{random.choice(["outdoors","indoors"])}'
            elif change_background == 'Remove Background':
                bad_tags.extend(ADD_BG)
                p.prompt = (p.prompt + ',' if p.prompt else '') + 'plain_background,simple_background,' + random.choice(COLORED_BG)
            elif change_background == 'Remove All':
                bad_tags.extend(COLORED_BG)
                bad_tags.extend(ADD_BG)
            if change_color == 'Colored':
                bad_tags.extend(BW_BG)
            elif change_color == 'Limited Palette':
                p.prompt = (p.prompt + ',' if p.prompt else '') + '(limited_palette:1.3)'
            elif change_color == 'Monochrome':
                p.prompt = (p.prompt + ',' if p.prompt else '') + ','.join(BW_BG)
            
            add_tags = ''
            if tags != '':
                add_tags = f'&tags=-animated+{tags.replace(",", "+")}'
                if mature_rating != 'All':
                    add_tags += f'+rating:{RATINGS[booru][mature_rating]}'
            else:
                add_tags = '&tags=-animated'
            
            # Getting Data
            api_url = ''
            random_post = {'preview_url':''}
            prompts = []
            last_img = []
            data = {'post': [{'tags': ''}]}
            preview_urls = []
            api_url = booru_apis.get(booru, Gelbooru())
            print(f'Using {booru}')

            data = api_url.get_data(add_tags, max_pages, post_url)
            print(api_url.booru_url)
            # Replace null scores with 0
            for post in data['post']:
                if post['score'] == None:
                    post['score'] = 0
            # Sort based on sorting_order
            if sorting_order == 'High Score':
                data['post'] = sorted(data['post'], key=lambda k: k.get('score', 0), reverse=True)
            elif sorting_order == 'Low Score':
                data['post'] = sorted(data['post'], key=lambda k: k.get('score', 0))
            random_number = self.random_number(sorting_order)
            if post_id:
                random_number = 0
            for _ in range(0, p.batch_size*p.n_iter):
                if same_prompt:
                    random_post = data['post'][random_number]
                else:
                    if not post_id:
                        random_number = self.random_number(sorting_order)
                    if mix_prompt:
                        temp_tags = []
                        max_tags = 0
                        for _ in range(0, mix_amount):
                            if not post_id:
                                random_number = self.random_number(sorting_order)
                            temp_tags.extend(data['post'][random_number]['tags'].split(' '))
                            max_tags = max(max_tags, len(data['post'][random_number]['tags'].split(' ')))
                        # distinct temp_tags
                        temp_tags = list(set(temp_tags))
                        random_post = data['post'][random_number]
                        if len(temp_tags) < max_tags:
                            max_tags = max(len(temp_tags), 20)
                        random_post['tags'] = ' '.join(random.sample(temp_tags, max_tags))
                    else:
                        try:
                            random_post = data['post'][random_number]
                        except IndexError:
                            raise Exception("No posts found with those tags. Try lowering the pages or changing the tags.")
                temp_tags = random_post['tags'].split(' ')
                if shuffle_tags:
                    temp_tags = random.sample(temp_tags, len(temp_tags))
                prompts.append(','.join(temp_tags))
                try:
                    preview_urls.append(random_post['file_url'])
                except KeyError:
                    print('No file_url found, using random pic')
                    preview_urls.append('https://pic.re/image')
                # Debug picture
                if DEBUG:
                    print(random_post)
            if use_img2img:
                if use_last_img:
                    response = requests.get(random_post['file_url'], headers=api_url.headers)
                    last_img = [Image.open(BytesIO(response.content))]
                else:
                    for img in preview_urls:
                        response = requests.get(img, headers=api_url.headers)
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
                if chaos_mode == 'Chaos':
                    p.prompt, p.negative_prompt = generate_chaos(p.prompt,p.negative_prompt,chaos_amount)
                elif chaos_mode == 'Less Chaos':
                    p.prompt, negative_prompt = generate_chaos(p.prompt,'',chaos_amount)
                    p.negative_prompt = p.negative_prompt+','+negative_prompt
            else:
                print('Processing Multiple Prompts')
                negative_prompts = []
                new_prompts = []
                if chaos_mode == 'Chaos':
                    for prompt in prompts:
                        tmp_prompt, negative_prompt = generate_chaos(prompt,p.negative_prompt,chaos_amount)
                        new_prompts.append(tmp_prompt)
                        negative_prompts.append(negative_prompt)
                    prompts = new_prompts
                    p.negative_prompt = negative_prompts
                elif chaos_mode == 'Less Chaos':
                    for prompt in prompts:
                        tmp_prompt, negative_prompt = generate_chaos(prompt,'',chaos_amount)
                        new_prompts.append(tmp_prompt)
                        negative_prompts.append(negative_prompt)
                    prompts = new_prompts
                    p.negative_prompt = [p.negative_prompt+','+negative_prompt for negative_prompt in negative_prompts]
                else:
                    p.negative_prompt = [p.negative_prompt for _ in range(0, p.batch_size*p.n_iter)]
                if p.prompt == '':
                    p.prompt = prompts
                else:
                    p.prompt = [f"{p.prompt},{prompt}" for prompt in prompts]
                if use_img2img:
                    if len(last_img) < p.batch_size*p.n_iter:
                        last_img = [last_img[0] for _ in range(0, p.batch_size*p.n_iter)]
            if negative_mode == 'Negative':
                #remove tags from p.prompt using tags from the original prompt
                orig_list = original_prompt.split(',')
                if type(p.prompt) == list:
                    new_positive_prompts = []
                    new_negative_prompts = []
                    for pr, np in zip(p.prompt, p.negative_prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = [tag for tag in clean_prompt if tag not in orig_list]
                        clean_prompt = ','.join(clean_prompt)
                        new_positive_prompts.append(original_prompt)
                        new_negative_prompts.append(f'{np},{clean_prompt}')
                    p.prompt = new_positive_prompts
                    p.negative_prompt = new_negative_prompts
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = [tag for tag in clean_prompt if tag not in orig_list]
                    clean_prompt = ','.join(clean_prompt)
                    p.negative_prompt = f'{p.negative_prompt},{clean_prompt}'
                    p.prompt = original_prompt
            if negative_mode == 'Negative' or chaos_mode in ['Chaos', 'Less Chaos']:
                # NEGATIVE PROMPT FIX
                neg_prompt_tokens = []
                for pr in p.negative_prompt:
                    neg_prompt_tokens.append(model_hijack.get_prompt_lengths(pr)[1])
                if len(set(neg_prompt_tokens)) != 1:
                    print('Padding negative prompts')
                    max_tokens = max(neg_prompt_tokens)
                    for num,neg in enumerate(neg_prompt_tokens):
                        while neg < max_tokens:
                            p.negative_prompt[num] += random.choice(p.negative_prompt[num].split(','))
                            # p.negative_prompt[num] += '_'
                            neg = model_hijack.get_prompt_lengths(p.negative_prompt[num])[1]
            if limit_tags < 1:
                # remove tags from p.prompt in percentage based on limit_tags
                if type(p.prompt) == list:
                    for num, pr in enumerate(p.prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = clean_prompt[:int(len(clean_prompt)*limit_tags)]
                        clean_prompt = ','.join(clean_prompt)
                        p.prompt[num] = clean_prompt
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = clean_prompt[:int(len(clean_prompt)*limit_tags)]
                    clean_prompt = ','.join(clean_prompt)
                    p.prompt = clean_prompt
            if max_tags > 0:
                if type(p.prompt) == list:
                    for num, pr in enumerate(p.prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = clean_prompt[:max_tags]
                        clean_prompt = ','.join(clean_prompt)
                        p.prompt[num] = clean_prompt
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = clean_prompt[:max_tags]
                    clean_prompt = ','.join(clean_prompt)
                    p.prompt = clean_prompt
                    
            # LORANADO
            p = self.loranado(lora_enabled,lora_folder,lora_amount,lora_min,lora_max,lora_custom_weights,p,lora_lock_prev)
                    
            if use_img2img:
                self.real_steps = p.steps
                p.steps = 1
                self.last_img = last_img
            else:
                pass
        elif lora_enabled:
            p = self.loranado(lora_enabled,lora_folder,lora_amount,lora_min,lora_max,lora_custom_weights,p,lora_lock_prev)
        else:
            pass
        
    def postprocess(self, p, processed, enabled, tags, booru, remove_bad_tags,max_pages,change_dash,same_prompt,remove_tags,use_img2img,denoising,use_last_img,change_background,change_color,shuffle_tags,post_id,mix_prompt,mix_amount,chaos_mode,negative_mode,chaos_amount,limit_tags,max_tags,sorting_order,mature_rating,lora_folder,lora_amount,lora_min,lora_max,lora_enabled,lora_custom_weights,lora_lock_prev):
        if use_img2img:
            print('Using pictures')
            width, height = self.check_orientation(self.last_img[0])
            p = StableDiffusionProcessingImg2Img(
                sd_model=shared.sd_model,
                outpath_samples=shared.opts.outdir_samples or shared.opts.outdir_img2img_samples,
                outpath_grids=shared.opts.outdir_grids or shared.opts.outdir_img2img_grids,
                prompt=p.prompt,
                negative_prompt=p.negative_prompt,
                seed=p.seed,
                sampler_name='Euler a',
                batch_size=p.batch_size,
                n_iter=p.n_iter,
                steps=self.real_steps,
                cfg_scale=p.cfg_scale,
                width=width,
                height=height,
                init_images=self.last_img,
                denoising_strength=denoising,
            )
            proc = process_images(p)
            processed.images = proc.images
            if use_last_img:
                    processed.images.append(self.last_img[0])
            else:
                for img in self.last_img:
                    processed.images.append(img)
        

    def random_number(self, sorting_order):
        # create weights so that the first element is more likely to be chosen than the next one
        weights = np.arange(POST_AMOUNT, 0, -1)
        weights = weights / weights.sum()
        if sorting_order in ('High Score', 'Low Score'):
            random_number = np.random.choice(np.arange(POST_AMOUNT), p=weights)
        else:
            random_number = random.randint(0, POST_AMOUNT-1)
        return random_number 