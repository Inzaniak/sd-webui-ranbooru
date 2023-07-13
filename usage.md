# Examples

## Basic Search
To do a basic search you'll need to set the following parameters:

### Required
- **Booru**: The booru you want to search on.
- **Tags to search (pre)**: The tags to search for on the booru. These should be the same used on a booru, but separated by a comma (e.g. `'1girl, solo'`).

### Optional
- **Max Pages**: This is the number of pages to search on the booru. Each page has 100 images, so if you set this to 5, it will search 500 images. This changes the variety of images you'll get.
- **Tags to remove (post)**: These are the tags to remove from the prompt after the search. (e.g. If you search for `'1girl, solo'` and remove `'solo'`, the final prompt won't have 'solo' in it.)
- **Use the same prompt for all images**: By default you'll get a different prompt for each image you create. If you want to use the same prompt for all images, set this to true.

## Post ID
You can search for a specific post ID by setting the following parameters:

### Required
- **Booru**: The booru you want to search on. Konachan and yande.re don't support this.
- **Post ID**: The ID of the post you want to search for. This is the number at the end of the URL of the post. (e.g. `https://danbooru.donmai.us/posts/123456` --> `123456`)

### Optional
- **Tags to remove (post)**: These are the tags to remove from the prompt after the search. (e.g. If you search for `'1girl, solo'` and remove `'solo'`, the final prompt won't have `'solo'` in it.)

## Img2Img
You can use the prompt plus the original image of the random booru pictures to create an img2img image. To do this, set the following parameters:

### Required
- **Booru**: The booru you want to search on.
- **Tags to search (pre)**: The tags to search for on the booru. These should be the same used on a booru, but separated by a comma (e.g. `'1girl, solo'`).
- **Use img2img**: Set this to true to use the img2img mode.

### Optional
- **Max Pages**: This is the number of pages to search on the booru. Each page has 100 images, so if you set this to 5, it will search 500 images. This changes the variety of images you'll get.
- **Tags to remove (post)**: These are the tags to remove from the prompt after the search. (e.g. If you search for `'1girl, solo'` and remove `'solo'`, the final prompt won't have 'solo' in it.)
- **Use the same prompt for all images**: By default you'll get a different prompt for each image you create. If you want to use the same prompt for all images, set this to true.
- **Denoising Strength**: This is the strength of the img2img denoiser. The higher the number, the more the picture will differ from the original. The default is 0.75.
- **Use last image as img2img**: By default you'll get a different image for each image you create. If you want to use the same image for all images, set this to true.

## Additional Modes
These can be used with the Basic Search and img2img examples.
### Mixing prompts
By enabling `Mix prompts` each image will be created using a mixture of N different booru posts where N is defined by the `Mix Amount` parameter.
### Chaos Mode
By enabling `Chaos Mode` each image will have an amount of tags moved to the negative prompt. The amount is defined by the `Chaos Amount` parameter, for example 0.5 means 50% of the tags will be moved to the negative prompt. Using the `Less Chaos` option won't move the tags you manually insert in the negative prompt.
### Negative Mode
By enabling `Negative Mode` each image will have all tags moved to the negative prompt.