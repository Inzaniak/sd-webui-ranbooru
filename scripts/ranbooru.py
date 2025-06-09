from io import BytesIO
import html
import random
import requests
import modules.scripts as scripts
import gradio as gr
import os
from PIL import Image
import numpy as np
import importlib
import requests_cache

from modules.processing import process_images, StableDiffusionProcessingImg2Img
from modules import shared
from modules.sd_hijack import model_hijack
from modules import deepbooru
from modules.ui_components import InputAccordion

extension_root = scripts.basedir()
user_data_dir = os.path.join(extension_root, 'user')
user_search_dir = os.path.join(user_data_dir, 'search')
user_remove_dir = os.path.join(user_data_dir, 'remove')
os.makedirs(user_search_dir, exist_ok=True)
os.makedirs(user_remove_dir, exist_ok=True)

if not os.path.isfile(os.path.join(user_search_dir, 'tags_search.txt')):
    with open(os.path.join(user_search_dir, 'tags_search.txt'), 'w'):
        pass
if not os.path.isfile(os.path.join(user_remove_dir, 'tags_remove.txt')):
    with open(os.path.join(user_remove_dir, 'tags_remove.txt'), 'w'):
        pass

COLORED_BG = ['black_background', 'aqua_background', 'white_background', 'colored_background', 'gray_background', 'blue_background', 'green_background', 'red_background', 'brown_background', 'purple_background', 'yellow_background', 'orange_background', 'pink_background', 'plain', 'transparent_background', 'simple_background', 'two-tone_background', 'grey_background']
ADD_BG = ['outdoors', 'indoors']
BW_BG = ['monochrome', 'greyscale', 'grayscale']
POST_AMOUNT = 100
COUNT = 100 #Number of images the search returned. Booru classes below were modified to update this value with the latest search result count.
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
    mature_ratings = gr.Radio.update(choices=RATINGS[booru].keys(), value="All")
    return mature_ratings


def show_fringe_benefits(booru):
    if booru == 'gelbooru':
        return gr.Checkbox.update(visible=True)
    else:
        return gr.Checkbox.update(visible=False)


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

    def get_data(self, add_tags, max_pages=10, id=''):
        pass

    def get_post(self, add_tags, max_pages=10, id=''):
        pass


class Gelbooru(Booru):

    def __init__(self, fringe_benefits):
        super().__init__('gelbooru', f'https://gelbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')
        self.fringeBenefits = fringe_benefits

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&pid={random.randint(0, max_pages-1)}{id}{add_tags}"
            # The randint function is an alias to randrange(a, b+1), so 'max_pages' should be passed as 'max_pages-1'
            if self.fringeBenefits:
                res = requests.get(self.booru_url, cookies={'fringeBenefits': 'yup'})
            else:
                res = requests.get(self.booru_url)
            data = res.json()
            COUNT = data['@attributes']['count']
            if COUNT <= max_pages*POST_AMOUNT:
                max_pages = COUNT // POST_AMOUNT+1
                # If max_pages is bigger than available pages, loop the function with updated max_pages based on the value of COUNT
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f" Processing {max_pages*POST_AMOUNT} out of {COUNT} results.")
            break
        return data

    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id=" + id)


class XBooru(Booru):

    def __init__(self):
        super().__init__('xbooru', f'https://xbooru.com/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&pid={random.randint(0, max_pages-1)}{id}{add_tags}"
            print(self.booru_url)
            res = requests.get(self.booru_url)
            data = res.json()
            COUNT = 0
            for post in data:
                post['file_url'] = f"https://xbooru.com/images/{post['directory']}/{post['image']}"
                COUNT += 1
            if COUNT <= max_pages*POST_AMOUNT:
                max_pages = COUNT // POST_AMOUNT+1
                # If max_pages is bigger than available pages, loop the function with updated max_pages based on the value of COUNT
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f" Processing {max_pages*POST_AMOUNT} out of {COUNT} results.")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id=" + id)


class Rule34(Booru):

    def __init__(self):
        super().__init__('rule34', f'https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&pid={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url)
            data = res.json()
            COUNT = len(data)
            if COUNT == 0:
                max_pages = 2
                # Rule34 does not have a way to know the amount of results available in the search, so we need to run the function again with a fixed amount of pages
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f"Found enough results")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id=" + id)


class Safebooru(Booru):

    def __init__(self):
        super().__init__('safebooru', f'https://safebooru.org/index.php?page=dapi&s=post&q=index&json=1&limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&pid={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url)
            data = res.json()
            COUNT = 0
            for post in data:
                post['file_url'] = f"https://safebooru.org/images/{post['directory']}/{post['image']}"
                COUNT += 1
            if COUNT <= max_pages*POST_AMOUNT:
                max_pages = COUNT // POST_AMOUNT+1
                # If max_pages is bigger than available pages, loop the function with updated max_pages based on the value of COUNT
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f" Processing {max_pages*POST_AMOUNT} out of {COUNT} results.")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        return self.get_data(add_tags, max_pages, "&id=" + id)


class Konachan(Booru):

    def __init__(self):
        super().__init__('konachan', f'https://konachan.com/post.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&page={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url)
            data = res.json()
            COUNT = len(data)
            if COUNT == 0:
                max_pages = 2
                # Konachan does not have a way to know the amount of results available in the search, so we need to run the function again with a fixed amount of pages
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f"Found enough results")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        raise Exception("Konachan does not support post IDs")


class Yandere(Booru):

    def __init__(self):
        super().__init__('yande.re', f'https://yande.re/post.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&page={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url)
            data = res.json()
            COUNT = len(data)
            COUNT = len(data)
            if COUNT == 0:
                max_pages = 2
                # Yandere does not have a way to know the amount of results available in the search, so we need to run the function again with a fixed amount of pages
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f"Found enough results")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        raise Exception("Yande.re does not support post IDs")


class AIBooru(Booru):

    def __init__(self):
        super().__init__('AIBooru', f'https://aibooru.online/posts.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&page={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url)
            data = res.json()
            for post in data:
                post['tags'] = post['tag_string']
            COUNT = len(data)
            if COUNT == 0:
                max_pages = 2
                # AIBooru does not have a way to know the amount of results available in the search, so we need to run the function again with a fixed amount of pages
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f"Found enough results")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        raise Exception("AIBooru does not support post IDs")


class Danbooru(Booru):

    def __init__(self):
        super().__init__('danbooru', f'https://danbooru.donmai.us/posts.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&page={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url, headers=self.headers)
            data = res.json()
            for post in data:
                post['tags'] = post['tag_string']
            COUNT = len(data)
            if COUNT == 0:
                max_pages = 2
                # Danbooru does not have a way to know the amount of results available in the search, so we need to run the function again with a fixed amount of pages
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f"Found enough results")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        self.booru_url = f"https://danbooru.donmai.us/posts/{id}.json"
        res = requests.get(self.booru_url, headers=self.headers)
        data = res.json()
        data['tags'] = data['tag_string']
        data = {'post': [data]}
        return data


class e621(Booru):

    def __init__(self):
        super().__init__('danbooru', f'https://e621.net/posts.json?limit={POST_AMOUNT}')

    def get_data(self, add_tags, max_pages=10, id=''):
        global COUNT
        loop_msg = True # avoid showing same msg twice
        for loop in range(2): # run loop at most twice
            if id:
                add_tags = ''
            self.booru_url = f"{self.booru_url}&page={random.randint(0, max_pages-1)}{id}{add_tags}"
            res = requests.get(self.booru_url, headers=self.headers)
            data = res.json()['posts']
            COUNT = len(data)
            for post in data:
                temp_tags = []
                sublevels = ['general', 'artist', 'copyright', 'character', 'species']
                for sublevel in sublevels:
                    temp_tags.extend(post['tags'][sublevel])
                post['tags'] = ' '.join(temp_tags)
                post['score'] = post['score']['total']
            if COUNT <= max_pages*POST_AMOUNT:
                max_pages = COUNT // POST_AMOUNT+1
                # If max_pages is bigger than available pages, loop the function with updated max_pages based on the value of COUNT
                while loop_msg:
                    print(f" Processing {COUNT} results.")
                    loop_msg = False
                    # avoid showing same msg twice
                continue
            else:
                print(f" Processing {max_pages*POST_AMOUNT} out of {COUNT} results.")
            break
        return {'post': data}

    def get_post(self, add_tags, max_pages=10, id=''):
        self.get_data(add_tags, max_pages, "&id=" + id)


def generate_chaos(pos_tags, neg_tags, chaos_amount):
    """Generates chaos in the prompt by adding random tags from the prompt to the positive and negative prompts

    Args:
        pos_tags (str): the positive prompt
        neg_tags (str): the negative prompt
        chaos_amount (float): the percentage of tags to put in the positive prompt

    Returns:
        str: the positive prompt
        str: the negative prompt
    """
    # create a list with the tags in the prompt and in the negative prompt
    chaos_list = [tag for tag in pos_tags.split(',') + neg_tags.split(',') if tag.strip() != '']
    # distinct the list
    chaos_list = list(set(chaos_list))
    random.shuffle(chaos_list)
    # put 50% of the tags in the prompt and the remaining 50% in the negative prompt
    len_list = round(len(chaos_list) * chaos_amount)
    pos_list = chaos_list[len_list:]
    pos_prompt = ','.join(pos_list)
    neg_list = chaos_list[:len_list]
    random.shuffle(neg_list)
    neg_prompt = ','.join(neg_list)
    return pos_prompt, neg_prompt


def resize_image(img, width, height, cropping=True):
    """Resize image to specified width and height

    Args:
        img (PIL.Image): the image
        width (int): the width in pixels
        height (int): the height in pixels
        cropping (bool): whether to crop the image or not

    Returns:
        PIL.Image: the resized image
    """
    if cropping:
        # resize the picture and center crop it
        # example: you have a 100x200 picture and width=300 and height=300
        # resize to 300x600 and crop to 300x300 from the center
        x, y = img.size
        if x < y:
            # scale to width keeping aspect ratio
            wpercent = (width / float(img.size[0]))
            hsize = int((float(img.size[1]) * float(wpercent)))
            img_new = img.resize((width, hsize))
            if img_new.size[1] < height:
                # scale to height keeping aspect ratio
                hpercent = (height / float(img.size[1]))
                wsize = int((float(img.size[0]) * float(hpercent)))
                img_new = img.resize((wsize, height))
        else:
            ypercent = (height / float(img.size[1]))
            wsize = int((float(img.size[0]) * float(ypercent)))
            img_new = img.resize((wsize, height))
            if img_new.size[0] < width:
                xpercent = (width / float(img.size[0]))
                hsize = int((float(img.size[1]) * float(xpercent)))
                img_new = img.resize((width, hsize))

        # crop center
        x, y = img_new.size
        left = (x - width) / 2
        top = (y - height) / 2
        right = (x + width) / 2
        bottom = (y + height) / 2
        img = img_new.crop((left, top, right, bottom))
    else:
        img = img.resize((width, height))
    return img

def modify_prompt(prompt, tagged_prompt, type_deepbooru):
    """Modifies the prompt based on the type_deepbooru selected

    Args:
        prompt (str): the prompt
        tagged_prompt (str): the prompt tagged by deepbooru
        type_deepbooru (str): the type of modification

    Returns:
        str: the modified prompt
    """
    if type_deepbooru == 'Add Before':
        return tagged_prompt + ',' + prompt
    elif type_deepbooru == 'Add After':
        return prompt + ',' + tagged_prompt
    elif type_deepbooru == 'Replace':
        return tagged_prompt
    return prompt

def remove_repeated_tags(prompt):
    """Removes the repeated tags keeping the same order

    Args:
        prompt (str): the prompt

    Returns:
        str: the prompt without repeated tags
    """
    prompt = prompt.split(',')
    new_prompt = []
    for tag in prompt:
        if tag not in new_prompt:
            new_prompt.append(tag)
    return ','.join(new_prompt)

def limit_prompt_tags(prompt, limit_tags, mode):
    """Limits the amount of tags in the prompt. It can be done by percentage or by a fixed amount.

    Args:
        prompt (str): the prompt
        limit_tags (float): the percentage of tags to keep
        mode (str): 'Limit' or 'Max'

    Returns:
        str: the prompt with the limited amount of tags
    """
    clean_prompt = prompt.split(',')
    if mode == 'Limit':
        clean_prompt = clean_prompt[:int(len(clean_prompt) * limit_tags)]
    elif mode == 'Max':
        clean_prompt = clean_prompt[:limit_tags]
    return ','.join(clean_prompt)

class Script(scripts.Script):
    previous_loras = ''
    last_img = []
    real_steps = 0
    version = "1.2"
    original_prompt = ''

    def get_files(self, path):
        files = []
        for file in os.listdir(path):
            if file.endswith('.txt'):
                files.append(file)
        return files

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

    def refresh_ser(self):
        return gr.update(choices=self.get_files(user_search_dir))
    def refresh_rem(self):
        return gr.update(choices=self.get_files(user_remove_dir))

    def ui(self, is_img2img):
        with InputAccordion(False, label="Ranbooru", elem_id=self.elem_id("ra_enable")) as enabled:
            booru = gr.Dropdown(
                ["gelbooru", "rule34", "safebooru", "danbooru", "konachan", 'yande.re', 'aibooru', 'xbooru', 'e621'], label="Booru", value="gelbooru")
            max_pages = gr.Slider(label="Max Pages", minimum=1, maximum=100, value=100, step=1)
            gr.Markdown("""## Post""")
            post_id = gr.Textbox(lines=1, label="Post ID")
            gr.Markdown("""## Tags""")
            tags = gr.Textbox(lines=1, label="Tags to Search (Pre)")
            remove_tags = gr.Textbox(lines=1, label="Tags to Remove (Post)")
            mature_rating = gr.Radio(list(RATINGS['gelbooru']), label="Mature Rating", value="All")
            remove_bad_tags = gr.Checkbox(label="Remove bad tags", value=True)
            shuffle_tags = gr.Checkbox(label="Shuffle tags", value=True)
            change_dash = gr.Checkbox(label='Convert "_" to spaces', value=False)
            same_prompt = gr.Checkbox(label="Use same prompt for all images", value=False)
            fringe_benefits = gr.Checkbox(label="Fringe Benefits", value=True)
            limit_tags = gr.Slider(value=1.0, label="Limit tags", minimum=0.05, maximum=1.0, step=0.05)
            max_tags = gr.Slider(value=100, label="Max tags", minimum=1, maximum=100, step=1)
            change_background = gr.Radio(["Don't Change", "Add Background", "Remove Background", "Remove All"], label="Change Background", value="Don't Change")
            change_color = gr.Radio(["Don't Change", "Colored", "Limited Palette", "Monochrome"], label="Change Color", value="Don't Change")
            sorting_order = gr.Radio(["Random", "High Score", "Low Score"], label="Sorting Order", value="Random")
            disable_prompt_modification = gr.Checkbox(label="Disable Ranbooru prompt modification", value=False) # New checkbox

            booru.change(get_available_ratings, booru, mature_rating)  # update available ratings
            booru.change(show_fringe_benefits, booru, fringe_benefits)  # display fringe benefits checkbox if gelbooru is selected

            gr.Markdown("""\n---\n""")
            with gr.Group():
                with gr.Accordion("Img2Img", open=False):
                    use_img2img = gr.Checkbox(label="Use img2img", value=False)
                    use_ip = gr.Checkbox(label="Send to Controlnet", value=False)
                    denoising = gr.Slider(value=0.75, label="Denoising", minimum=0.05, maximum=1.0, step=0.05)
                    use_last_img = gr.Checkbox(label="Use last image as img2img", value=False)
                    crop_center = gr.Checkbox(label="Crop Center", value=False)
                    use_deepbooru = gr.Checkbox(label="Use Deepbooru", value=False)
                    type_deepbooru = gr.Radio(["Add Before", "Add After", "Replace"], label="Deepbooru Tags Position", value="Add Before")
            with gr.Group():
                with gr.Accordion("File", open=False):
                    use_search_txt = gr.Checkbox(label="Use tags_search.txt", value=False)
                    choose_search_txt = gr.Dropdown(self.get_files(user_search_dir), label="Choose tags_search.txt", value="")
                    search_refresh_btn = gr.Button("Refresh")
                    use_remove_txt = gr.Checkbox(label="Use tags_remove.txt", value=False)
                    choose_remove_txt = gr.Dropdown(self.get_files(user_remove_dir), label="Choose tags_remove.txt", value="")
                    remove_refresh_btn = gr.Button("Refresh")
            with gr.Group():
                with gr.Accordion("Extra", open=False):
                    with gr.Box():
                        mix_prompt = gr.Checkbox(label="Mix prompts", value=False)
                        mix_amount = gr.Slider(value=2, label="Mix amount", minimum=2, maximum=10, step=1)
                    with gr.Box():
                        chaos_mode = gr.Radio(["None", "Chaos", "Less Chaos"], label="Chaos Mode", value="None")
                        chaos_amount = gr.Slider(value=0.5, label="Chaos Amount %", minimum=0.1, maximum=1, step=0.05)
                    with gr.Box():
                        negative_mode = gr.Radio(["None", "Negative"], label="Negative Mode", value="None")
                        use_same_seed = gr.Checkbox(label="Use same seed for all pictures", value=False)
                    with gr.Box():
                        use_cache = gr.Checkbox(label="Use cache", value=True)
        with InputAccordion(False, label="LoRAnado", elem_id=self.elem_id("lo_enable")) as lora_enabled:
            with gr.Box():
                lora_lock_prev = gr.Checkbox(label="Lock previous LoRAs", value=False)
                lora_folder = gr.Textbox(lines=1, label="LoRAs Subfolder")
                lora_amount = gr.Slider(value=1, label="LoRAs Amount", minimum=1, maximum=10, step=1)
            with gr.Box():
                lora_min = gr.Slider(value=-1.0, label="Min LoRAs Weight", minimum=-1.0, maximum=1, step=0.1)
                lora_max = gr.Slider(value=1.0, label="Max LoRAs Weight", minimum=-1.0, maximum=1.0, step=0.1)
                lora_custom_weights = gr.Textbox(lines=1, label="LoRAs Custom Weights")

        search_refresh_btn.click(
            fn=self.refresh_ser,
            inputs=[],
            outputs=[choose_search_txt]
        )

        remove_refresh_btn.click(
            fn=self.refresh_rem,
            inputs=[],
            outputs=[choose_remove_txt]
        )

        return [enabled, tags, booru, remove_bad_tags, max_pages, change_dash, same_prompt, fringe_benefits, remove_tags, use_img2img, denoising, use_last_img, change_background, change_color, shuffle_tags, post_id, mix_prompt, mix_amount, chaos_mode, negative_mode, chaos_amount, limit_tags, max_tags, sorting_order, mature_rating, lora_folder, lora_amount, lora_min, lora_max, lora_enabled, lora_custom_weights, lora_lock_prev, use_ip, use_search_txt, use_remove_txt, choose_search_txt, choose_remove_txt, search_refresh_btn, remove_refresh_btn, crop_center, use_deepbooru, type_deepbooru, use_same_seed, use_cache, disable_prompt_modification] # Added to return list

    def check_orientation(self, img):
        """Check if image is portrait, landscape or square"""
        x, y = img.size
        if x / y > 1.2:
            return [768, 512]
        elif y / x > 1.2:
            return [512, 768]
        else:
            return [768, 768]

    def loranado(self, lora_enabled, lora_folder, lora_amount, lora_min, lora_max, lora_custom_weights, p, lora_lock_prev):
        lora_prompt = ''
        if lora_enabled:
            if lora_lock_prev:
                lora_prompt = self.previous_loras
            else:
                loras = []
                loras = os.listdir(f'{lora_folder}')
                # get only .safetensors files
                loras = [lora.replace('.safetensors', '') for lora in loras if lora.endswith('.safetensors')]
                for l in range(0, lora_amount):
                    lora_weight = 0
                    if lora_custom_weights != '':
                        lora_weight = float(lora_custom_weights.split(',')[l])
                    while lora_weight == 0:
                        lora_weight = round(random.uniform(lora_min, lora_max), 1)
                    lora_prompt += f'<lora:{random.choice(loras)}:{lora_weight}>'
                    self.previous_loras = lora_prompt
        if lora_prompt:
            if isinstance(p.prompt, list):
                for num, pr in enumerate(p.prompt):
                    p.prompt[num] = f'{lora_prompt} {pr}'
            else:
                p.prompt = f'{lora_prompt} {p.prompt}'
        return p

    def before_process(self, p, enabled, tags, booru, remove_bad_tags, max_pages, change_dash, same_prompt, fringe_benefits, remove_tags, use_img2img, denoising, use_last_img, change_background, change_color, shuffle_tags, post_id, mix_prompt, mix_amount, chaos_mode, negative_mode, chaos_amount, limit_tags, max_tags, sorting_order, mature_rating, lora_folder, lora_amount, lora_min, lora_max, lora_enabled, lora_custom_weights, lora_lock_prev, use_ip, use_search_txt, use_remove_txt, choose_search_txt, choose_remove_txt, search_refresh_btn, remove_refresh_btn, crop_center, use_deepbooru, type_deepbooru, use_same_seed, use_cache, disable_prompt_modification): # Added disable_prompt_modification parameter
        # Manage Cache
        if use_cache and not requests_cache.patcher.is_installed():
            requests_cache.install_cache('ranbooru_cache', backend='sqlite', expire_after=3600)
        elif not use_cache and requests_cache.patcher.is_installed():
            requests_cache.uninstall_cache()
        if enabled:
            # If disable_prompt_modification is checked, skip all prompt modifications
            if disable_prompt_modification:
                if lora_enabled: # Still apply LoRAs if lora_enabled
                    p = self.loranado(lora_enabled, lora_folder, lora_amount, lora_min, lora_max, lora_custom_weights, p, lora_lock_prev)
                return

            # Initialize APIs
            booru_apis = {
                'gelbooru': Gelbooru(fringe_benefits),
                'rule34': Rule34(),
                'safebooru': Safebooru(),
                'danbooru': Danbooru(),
                'konachan': Konachan(),
                'yande.re': Yandere(),
                'aibooru': AIBooru(),
                'xbooru': XBooru(),
                'e621': e621(),
            }
            self.original_prompt = p.prompt
            # Check if compatible
            check_exception(booru, {'tags': tags, 'post_id': post_id})

            # Manage Bad Tags
            bad_tags = []
            if remove_bad_tags:
                bad_tags = ['mixed-language_text', 'watermark', 'text', 'english_text', 'speech_bubble', 'signature', 'artist_name', 'censored', 'bar_censor', 'translation', 'twitter_username', "twitter_logo", 'patreon_username', 'commentary_request', 'tagme', 'commentary', 'character_name', 'mosaic_censoring', 'instagram_username', 'text_focus', 'english_commentary', 'comic', 'translation_request', 'fake_text', 'translated', 'paid_reward_available', 'thought_bubble', 'multiple_views', 'silent_comic', 'out-of-frame_censoring', 'symbol-only_commentary', '3koma', '2koma', 'character_watermark', 'spoken_question_mark', 'japanese_text', 'spanish_text', 'language_text', 'fanbox_username', 'commission', 'original', 'ai_generated', 'stable_diffusion', 'tagme_(artist)', 'text_bubble', 'qr_code', 'chinese_commentary', 'korean_text', 'partial_commentary', 'chinese_text', 'copyright_request', 'heart_censor', 'censored_nipples', 'page_number', 'scan', 'fake_magazine_cover', 'korean_commentary']

            if ',' in remove_tags:
                bad_tags.extend(remove_tags.split(','))
            else:
                bad_tags.append(remove_tags)

            if use_remove_txt:
                with open(os.path.join(user_remove_dir, choose_remove_txt), 'r') as f:
                    tags_to_remove_from_file = [line.strip() for line in f if line.strip()]
                bad_tags.extend(tags_to_remove_from_file)

            # Manage Backgrounds
            background_options = {
                'Add Background': ('detailed_background,' + random.choice(["outdoors", "indoors"]), COLORED_BG),
                'Remove Background': ('plain_background,simple_background,' + random.choice(COLORED_BG), ADD_BG),
                'Remove All': ('', COLORED_BG + ADD_BG)
            }

            if change_background in background_options:
                prompt_addition, tags_to_remove = background_options[change_background]
                bad_tags.extend(tags_to_remove)
                p.prompt = f'{p.prompt},{prompt_addition}' if p.prompt else prompt_addition

            # Manage Colors
            color_options = {
                'Colored': BW_BG,
                'Limited Palette': '(limited_palette:1.3)',
                'Monochrome': ','.join(BW_BG)
            }

            if change_color in color_options:
                color_option = color_options[change_color]
                if isinstance(color_option, list):
                    bad_tags.extend(color_option)
                else:
                    p.prompt = f'{p.prompt},{color_option}' if p.prompt else color_option

            if use_search_txt:
                with open(os.path.join(user_search_dir, choose_search_txt), 'r') as f:
                    possible_search_lines = [line.strip() for line in f if line.strip()]
                if possible_search_lines: # Ensure the list is not empty
                    selected_tags_line = random.choice(possible_search_lines)
                    tags = f'{tags},{selected_tags_line}' if tags else selected_tags_line

            add_tags = '&tags=-animated'
            if tags:
                add_tags += f'+{tags.replace(",", "+")}'
                if mature_rating != 'All':
                    add_tags += f'+rating:{RATINGS[booru][mature_rating]}'

            # Getting Data
            random_post = {'preview_url': ''}
            prompts = []
            last_img = []
            preview_urls = []
            api_url = booru_apis.get(booru, Gelbooru(fringe_benefits))
            print(f'Using {booru}')

            # Manage Post ID
            if post_id:
                data = api_url.get_post(add_tags, max_pages, post_id)
            else:
                data = api_url.get_data(add_tags, max_pages)

            print(api_url.booru_url)
            # Replace null scores with 0s
            for post in data['post']:
                post['score'] = post.get('score', 0)
            # Sort based on sorting_order
            if sorting_order == 'High Score':
                data['post'] = sorted(data['post'], key=lambda k: k.get('score', 0), reverse=True)
            elif sorting_order == 'Low Score':
                data['post'] = sorted(data['post'], key=lambda k: k.get('score', 0))
            if post_id:
                print(f'Using post ID: {post_id}')
                random_numbers = [0 for _ in range(0, p.batch_size * p.n_iter)]
            else:
                random_numbers = self.random_number(sorting_order, p.batch_size * p.n_iter)
            for random_number in random_numbers:
                if same_prompt:
                    random_post = data['post'][random_numbers[0]]
                else:
                    if mix_prompt:
                        temp_tags = []
                        max_tags = 0
                        for _ in range(0, mix_amount):
                            if not post_id:
                                random_mix_number = self.random_number(sorting_order, 1)[0]
                            temp_tags.extend(data['post'][random_mix_number]['tags'].split(' '))
                            max_tags = max(max_tags, len(data['post'][random_mix_number]['tags'].split(' ')))
                        # distinct temp_tags
                        temp_tags = list(set(temp_tags))
                        random_post = data['post'][random_number]
                        max_tags = min(max(len(temp_tags), 20), max_tags)
                        random_post['tags'] = ' '.join(random.sample(temp_tags, max_tags))
                    else:
                        try:
                            random_post = data['post'][random_number]
                        except IndexError:
                            raise Exception(
                                "No posts found with those tags. Try lowering the pages or changing the tags.")
                clean_tags = random_post['tags'].replace('(', r'\(').replace(')', r'\)')
                temp_tags = random.sample(clean_tags.split(' '), len(clean_tags.split(' '))) if shuffle_tags else clean_tags.split(' ')
                prompts.append(','.join(temp_tags))
                preview_urls.append(random_post.get('file_url', 'https://pic.re/image'))
                # Debug picture
                if DEBUG:
                    print(random_post)
            # Get Images
            if use_img2img or use_deepbooru:
                image_urls = [random_post['file_url']] if use_last_img else preview_urls

                for img in image_urls:
                    response = requests.get(img, headers=api_url.headers)
                    last_img.append(Image.open(BytesIO(response.content)))
            new_prompts = []
            # Cleaning Tags
            for prompt in prompts:
                prompt_tags = [tag for tag in html.unescape(prompt).split(',') if tag.strip() not in bad_tags]
                for bad_tag in bad_tags:
                    if '*' in bad_tag:
                        prompt_tags = [tag for tag in prompt_tags if bad_tag.replace('*', '') not in tag]
                new_prompt = ','.join(prompt_tags)
                if change_dash:
                    new_prompt = new_prompt.replace("_", " ")
                new_prompts.append(new_prompt)
            prompts = new_prompts
            if len(prompts) == 1:
                print('Processing Single Prompt')
                # Check if the prompt has been modified by dynamic prompts
                if "__" in p.prompt:
                    p.prompt = f"{p.prompt},{prompts[-1]}" # Append to existing prompt
                else:
                    p.prompt = f"{self.original_prompt},{prompts[-1]}" if self.original_prompt else prompts[-1] # Keep original behavior

                if chaos_mode in ['Chaos', 'Less Chaos']:
                    negative_prompt = '' if chaos_mode == 'Less Chaos' else p.negative_prompt
                    p.prompt, negative_prompt = generate_chaos(p.prompt, negative_prompt, chaos_amount)
                    p.negative_prompt = f"{p.negative_prompt},{negative_prompt}" if p.negative_prompt else negative_prompt
            else:
                print('Processing Multiple Prompts')
                negative_prompts = []
                new_prompts_list = [] # Renamed to avoid conflict
                if chaos_mode == 'Chaos':
                    for prompt in prompts:
                        tmp_prompt, negative_prompt = generate_chaos(prompt, p.negative_prompt, chaos_amount)
                        new_prompts_list.append(tmp_prompt)
                        negative_prompts.append(negative_prompt)
                    prompts = new_prompts_list
                    p.negative_prompt = negative_prompts
                elif chaos_mode == 'Less Chaos':
                    for prompt in prompts:
                        tmp_prompt, negative_prompt = generate_chaos(prompt, '', chaos_amount)
                        new_prompts_list.append(tmp_prompt)
                        negative_prompts.append(negative_prompt)
                    prompts = new_prompts_list
                    p.negative_prompt = [p.negative_prompt + ',' + negative_prompt for negative_prompt in negative_prompts] # Original behavior: p.negative_prompt should be a list of strings
                else:
                    p.negative_prompt = [p.negative_prompt for _ in range(0, p.batch_size * p.n_iter)]

                # Check if the prompt has been modified by dynamic prompts
                if "__" in p.prompt:
                    p.prompt = [f"{p.prompt},{prompt}" for prompt in prompts] # Append to existing prompt
                else:
                    p.prompt = prompts if not self.original_prompt else [f"{self.original_prompt},{prompt}" for prompt in prompts] # Keep original behavior


                if use_img2img:
                    if len(last_img) < p.batch_size * p.n_iter:
                        last_img = [last_img[0] for _ in range(0, p.batch_size * p.n_iter)]
            if negative_mode == 'Negative':
                # remove tags from p.prompt using tags from the original prompt
                orig_list = self.original_prompt.split(',')
                if isinstance(p.prompt, list):
                    new_positive_prompts = []
                    new_negative_prompts = []
                    for pr, npp in zip(p.prompt, p.negative_prompt):
                        clean_prompt = pr.split(',')
                        clean_prompt = [tag for tag in clean_prompt if tag not in orig_list]
                        clean_prompt = ','.join(clean_prompt)
                        new_positive_prompts.append(self.original_prompt)
                        new_negative_prompts.append(f'{npp},{clean_prompt}')
                    p.prompt = new_positive_prompts
                    p.negative_prompt = new_negative_prompts
                else:
                    clean_prompt = p.prompt.split(',')
                    clean_prompt = [tag for tag in clean_prompt if tag not in orig_list]
                    clean_prompt = ','.join(clean_prompt)
                    p.negative_prompt = f'{p.negative_prompt},{clean_prompt}'
                    p.prompt = self.original_prompt
            if negative_mode == 'Negative' or chaos_mode in ['Chaos', 'Less Chaos']:
                # NEGATIVE PROMPT FIX
                neg_prompt_tokens = []
                for pr in p.negative_prompt:
                    neg_prompt_tokens.append(model_hijack.get_prompt_lengths(pr)[1])
                if len(set(neg_prompt_tokens)) != 1:
                    print('Padding negative prompts')
                    max_tokens = max(neg_prompt_tokens)
                    for num, neg in enumerate(neg_prompt_tokens):
                        while neg < max_tokens:
                            p.negative_prompt[num] += random.choice(p.negative_prompt[num].split(','))
                            # p.negative_prompt[num] += '_'
                            neg = model_hijack.get_prompt_lengths(p.negative_prompt[num])[1]

            if limit_tags < 1:
                if isinstance(p.prompt, list):
                    p.prompt = [limit_prompt_tags(pr, limit_tags, 'Limit') for pr in p.prompt]
                else:
                    p.prompt = limit_prompt_tags(p.prompt, limit_tags, 'Limit')

            if max_tags > 0:
                if isinstance(p.prompt, list):
                    p.prompt = [limit_prompt_tags(pr, max_tags, 'Max') for pr in p.prompt]
                else:
                    p.prompt = limit_prompt_tags(p.prompt, max_tags, 'Max')

            if use_same_seed:
                p.seed = random.randint(0, 2 ** 32 - 1) if p.seed == -1 else p.seed
                p.seed = [p.seed] * p.batch_size

            # LORANADO
            p = self.loranado(lora_enabled, lora_folder, lora_amount, lora_min, lora_max, lora_custom_weights, p, lora_lock_prev)
            if use_deepbooru and not use_img2img:
                self.last_img = last_img
                tagged_prompts = self.use_autotagger('deepbooru')

                if isinstance(p.prompt, list):
                    p.prompt = [modify_prompt(pr, tagged_prompts[num], type_deepbooru) for num, pr in enumerate(p.prompt)]
                    p.prompt = [remove_repeated_tags(pr) for pr in p.prompt]
                else:
                    p.prompt = modify_prompt(p.prompt, tagged_prompts, type_deepbooru)
                    p.prompt = remove_repeated_tags(p.prompt[0])

            if use_img2img:
                if not use_ip:
                    self.real_steps = p.steps
                    p.steps = 1
                    self.last_img = last_img
                if use_ip:
                    controlNetModule = importlib.import_module('extensions.sd-webui-controlnet.scripts.external_code', 'external_code')
                    controlNetList = controlNetModule.get_all_units_in_processing(p)
                    copied_network = controlNetList[0].__dict__.copy()
                    copied_network['enabled'] = True
                    copied_network['weight'] = denoising
                    array_img = np.array(last_img[0])
                    copied_network['image']['image'] = array_img
                    copied_networks = [copied_network] + controlNetList[1:]
                    controlNetModule.update_cn_script_in_processing(p, copied_networks)

        elif lora_enabled:
            p = self.loranado(lora_enabled, lora_folder, lora_amount, lora_min, lora_max, lora_custom_weights, p, lora_lock_prev)

    def postprocess(self, p, processed, enabled, tags, booru, remove_bad_tags, max_pages, change_dash, same_prompt, fringe_benefits, remove_tags, use_img2img, denoising, use_last_img, change_background, change_color, shuffle_tags, post_id, mix_prompt, mix_amount, chaos_mode, negative_mode, chaos_amount, limit_tags, max_tags, sorting_order, mature_rating, lora_folder, lora_amount, lora_min, lora_max, lora_enabled, lora_custom_weights, lora_lock_prev, use_ip, use_search_txt, use_remove_txt, choose_search_txt, choose_remove_txt, search_refresh_btn, remove_refresh_btn, crop_center, use_deepbooru, type_deepbooru, use_same_seed, use_cache):
        if use_img2img and not use_ip and enabled:
            print('Using pictures')
            if crop_center:
                width, height = p.width, p.height
                self.last_img = [resize_image(img, width, height, cropping=True) for img in self.last_img]
            else:
                width, height = self.check_orientation(self.last_img[0])
            final_prompts = p.prompt
            if use_deepbooru:
                tagged_prompts = self.use_autotagger('deepbooru')
                if isinstance(p.prompt, list):
                    final_prompts = [modify_prompt(pr, tagged_prompts[num], type_deepbooru) for num, pr in enumerate(p.prompt)]
                    final_prompts = [remove_repeated_tags(pr) for pr in final_prompts]
                else:
                    final_prompts = modify_prompt(p.prompt, tagged_prompts, type_deepbooru)
                    final_prompts = remove_repeated_tags(final_prompts)
            p = StableDiffusionProcessingImg2Img(
                sd_model=shared.sd_model,
                outpath_samples=shared.opts.outdir_samples or shared.opts.outdir_img2img_samples,
                outpath_grids=shared.opts.outdir_grids or shared.opts.outdir_img2img_grids,
                prompt=final_prompts,
                negative_prompt=p.negative_prompt,
                seed=p.seed,
                sampler_name=p.sampler_name,
                scheduler=p.scheduler,
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
            processed.infotexts = proc.infotexts
            if use_last_img:
                processed.images.append(self.last_img[0])
            else:
                for num, img in enumerate(self.last_img):
                    processed.images.append(img)
                    processed.infotexts.append(proc.infotexts[num + 1])

    def random_number(self, sorting_order, size):
        """Generates random numbers based on the sorting_order

        Args:
            sorting_order (str): the sorting order. It can be 'Random', 'High Score' or 'Low Score'
            size (int): the amount of random numbers to generate

        Returns:
            list: the random numbers
        """
        global COUNT
        if COUNT > POST_AMOUNT: # Modified to use COUNT instead of POST_AMOUNT
            COUNT = POST_AMOUNT # If there are more than 100 images, use POST_AMOUNT
        weights = np.arange(COUNT, 0, -1)
        weights = weights / weights.sum()
        if sorting_order in ('High Score', 'Low Score'):
            random_numbers = np.random.choice(np.arange(COUNT), size=size, p=weights, replace=False)
        else:
            random_numbers = random.sample(range(COUNT), size)
        return random_numbers

    def use_autotagger(self, model):
        """Use the autotagger to tag the images

        Args:
            model (str): the model to use. Right now only 'deepbooru' is supported

        Returns:
            list: the tagged prompts
        """
        if model == 'deepbooru':
            if isinstance(self.original_prompt, str):
                orig_prompt = [self.original_prompt]
            else:
                orig_prompt = self.original_prompt
            deepbooru.model.start()
            for img, prompt in zip(self.last_img, orig_prompt):
                final_prompts = [prompt + ',' + deepbooru.model.tag_multi(img) for img in self.last_img]
            deepbooru.model.stop()
            return final_prompts
