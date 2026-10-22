"""Crop reviewed sprite rectangles and package PNGs. Requires Pillow; no Unity side effects."""
import argparse
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import zipfile
from PIL import Image, ImageChops, ImageDraw


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_name(value):
    require(isinstance(value, str) and '\\' not in value and ':' not in value, 'Unsafe output path')
    name = PurePosixPath(value)
    require(not name.is_absolute() and name.suffix.lower() == '.png' and '..' not in name.parts,
            'Output must be a relative PNG path without traversal')
    require(all(p and p != '.' for p in value.split('/')), 'Invalid output path segment')
    require(all(p.split('.')[0].upper() not in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(1,10)],*[f'LPT{i}' for i in range(1,10)]} for p in name.parts), 'Reserved output path')
    return name


def build(plan_path, output):
    plan_path, output = plan_path.resolve(), output.resolve()
    require(not output.exists() or not any(output.iterdir()), 'Preserving non-empty output; choose a new directory')
    zip_path = output.with_name(output.name + '.zip')
    require(not zip_path.exists(), 'Preserving existing ZIP; choose a new output name')
    plan = json.loads(plan_path.read_text(encoding='utf-8-sig'))
    base = plan_path.parent
    require(isinstance(plan.get('sources'), dict) and plan['sources'], 'sources required')
    require(isinstance(plan.get('sprites'), list) and plan['sprites'], 'sprites required')
    sources = {}
    for key, info in plan['sources'].items():
        path = (base / info['path']).resolve()
        with Image.open(path) as opened:
            image = opened.convert('RGBA')
        require(list(image.size) == info['size'], f'Source dimensions changed: {key}: {image.size} != {info["size"]}')
        sources[key] = (image, info['path'])
    # Validate every crop before writing deliverables, so a bad plan cannot leave a plausible partial ZIP.
    prepared, names = [], set()
    for item in plan['sprites']:
        name = safe_name(item['path'])
        require(str(name).casefold() not in names, f'Duplicate sprite: {name}')
        names.add(str(name).casefold())
        require(item.get('source') in sources, f'Unknown source: {name}')
        source, source_path = sources[item['source']]
        box = item['rect']
        require(len(box) == 4 and all(type(x) is int for x in box), f'Integer rect required: {name}')
        l,t,r,b = box
        require(0 <= l < r <= source.width and 0 <= t < b <= source.height, f'Out-of-bounds rect: {name}')
        image = source.crop(box)
        if item.get('mask'):
            with Image.open(base / item['mask']) as mask_image:
                require(mask_image.size == source.size, f'Mask/source size mismatch: {name}')
                mask = mask_image.getchannel('A') if 'A' in mask_image.getbands() else mask_image.convert('L')
                image.putalpha(ImageChops.multiply(image.getchannel('A'), mask.crop(box)))
        radius = item.get('roundRadius', 0)
        require(isinstance(radius, (int,float)) and 0 <= radius <= min(image.size)/2, f'Invalid radius: {name}')
        if radius:
            mask = Image.new('L', (image.width*4,image.height*4))
            ImageDraw.Draw(mask).rounded_rectangle((0,0,mask.width-1,mask.height-1), radius=radius*4, fill=255)
            image.putalpha(ImageChops.multiply(image.getchannel('A'), mask.resize(image.size, Image.Resampling.LANCZOS)))
        trim_offset = [0,0]
        if item.get('trim'):
            alpha_box = image.getchannel('A').getbbox()
            require(alpha_box is not None, f'Empty sprite: {name}')
            trim_offset = list(alpha_box[:2])
            image = image.crop(alpha_box)
        padding = item.get('padding', [0,0,0,0])
        require(len(padding) == 4 and all(type(x) is int and x >= 0 for x in padding), f'Invalid padding: {name}')
        if any(padding):
            pl,pt,pr,pb = padding
            padded = Image.new('RGBA', (image.width+pl+pr,image.height+pt+pb))
            padded.paste(image,(pl,pt))
            image = padded
        border = {key:item.get('border',{}).get(key,0) for key in ('left','bottom','right','top')}
        require(all(type(v) is int and v >= 0 for v in border.values()), f'Invalid border: {name}')
        require(border['left']+border['right'] < image.width and border['top']+border['bottom'] < image.height, f'Border consumes center: {name}')
        require(not item.get('fixedSize') or not any(border.values()), f'Fixed composite cannot be nine-sliced: {name}')
        alpha_min, alpha_max = image.getchannel('A').getextrema()
        require(alpha_max > 0, f'Fully transparent sprite: {name}')
        require(alpha_min < 255 or item.get('role') == 'background' or (item.get('allowOpaque') and item.get('note')), f'Non-background is fully opaque: {name}')
        record = dict(path=name.as_posix(), size=list(image.size), source=source_path, sourceRect=box,
                      trimOffset=trim_offset, padding=padding, border=border, fixedSize=bool(item.get('fixedSize')),
                      alphaMin=alpha_min, alphaMax=alpha_max, note=item.get('note',''))
        prepared.append((name,image,record))
    output.mkdir(parents=True,exist_ok=True)
    for name,image,record in prepared:
        target = output / str(name)
        target.parent.mkdir(parents=True,exist_ok=True)
        image.save(target)
        with Image.open(target) as check:
            check.verify()
        record['sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest = {k:plan[k] for k in ('name','referenceResolution','texts','limits') if k in plan}
    manifest['coordinateOrigin'] = 'top-left'
    manifest['sprites'] = [record for _,_,record in prepared]
    (output/'slices.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    columns,cw,ch = 5,240,210
    sheet = Image.new('RGB',(columns*cw,math.ceil(len(prepared)/columns)*ch),'#f5f7fc')
    draw = ImageDraw.Draw(sheet)
    for i,(name,image,record) in enumerate(prepared):
        x,y = i%columns*cw,i//columns*ch
        for py in range(y+25,y+ch-20,12):
            for px in range(x+5,x+cw-5,12):
                draw.rectangle((px,py,min(px+11,x+cw-6),min(py+11,y+ch-21)),fill='#d4dae6' if ((px-x)//12+(py-y)//12)%2 else '#eef1f7')
        thumb = image.copy(); thumb.thumbnail((cw-18,ch-56),Image.Resampling.LANCZOS)
        sheet.paste(thumb,(x+(cw-thumb.width)//2,y+29+(ch-56-thumb.height)//2),thumb)
        draw.text((x+8,y+5),name.as_posix().encode('ascii','replace').decode(),fill='#182338')
        draw.text((x+8,y+ch-18),f'{image.width} x {image.height}',fill='#424b5b')
    sheet.save(output/'CONTACT_SHEET.jpg',quality=93)
    (output/'README.md').write_text('PNG sprite package. No Unity import.\n\nUse slices.json for source rectangles, sizes, trim offsets, padding and borders (left,bottom,right,top). Keep icon aspect ratios; nine-slice only blank plates. Preview checkerboard is not baked into PNGs. Text/number images cover supplied glyphs only. AI reconstructed details may differ from the reference. See per-sprite notes and limits. Automated validation does not replace visual review.\n',encoding='utf8')
    validation = dict(pngCount=len(prepared),pngDecode='PASS',nonEmpty='PASS',alphaChecks='PASS',
                      borders='PASS',unityImported=False,visualReview='required')
    (output/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf8')
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(output.rglob('*')):
            if file.is_file(): archive.write(file,Path(output.name)/file.relative_to(output))
    with zipfile.ZipFile(zip_path) as archive:
        require(archive.testzip() is None,'ZIP integrity failure')
    print(json.dumps(dict(pngCount=len(prepared),output=str(output),zip=str(zip_path),zipIntegrity='PASS'),ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    build(args.plan,args.output)
