import io
import sys
from PIL import Image

def get_ascii_frame(img, angle=0):
    rotated = img.rotate(angle, resample=Image.BICUBIC, fillcolor=(0,0,0,0))
    resized = rotated.resize((30, 15))
    pixels = resized.load()
    chars = ' ░▒▓█'
    frame = []
    for y in range(15):
        row = ''
        for x in range(30):
            r,g,b,a = pixels[x,y]
            if a < 50:
                row += ' '
            else:
                intensity = (r+g+b)/3
                idx = int((intensity / 255) * (len(chars)-1))
                row += chars[idx]
        frame.append(row)
    return '\n'.join(frame)

img = Image.open(r'd:\HelloWorld\Projects\WhatsMyNote\docs\assets\logo.png').convert('RGBA')
frames = []
for i in range(4):
    frames.append(get_ascii_frame(img, i * -90))
    
with open('whatsmynote/app/logo_frames.py', 'w', encoding='utf-8') as f:
    f.write('FRAMES = [\n')
    for frame in frames:
        f.write('    """\n' + frame + '\n""",\n')
    f.write(']\n')
