from io import BytesIO
import re
from flask import Flask, request, send_file, render_template, abort, send_from_directory
from PIL import Image
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    SquareModuleDrawer, RoundedModuleDrawer, CircleModuleDrawer
)
from qrcode.image.styles.colormasks import SolidFillColorMask  # for colours

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2 MB upload cap

HEX = re.compile(r'^#(?:[0-9a-fA-F]{3}){1,2}$')

def hex_to_rgb(h: str):
    h = h.lstrip('#')
    if len(h) == 3:  # e.g. #fff
        h = ''.join(2*c for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def drawer(style):
    return {
        'circle':  CircleModuleDrawer(),
        'rounded': RoundedModuleDrawer(),
    }.get(style, SquareModuleDrawer())

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')

    data  = request.form.get('qrdata', '').strip()
    fghex = request.form.get('fg', '#000000')
    bghex = request.form.get('bg', '#ffffff')
    style = request.form.get('style', 'square')
    file  = request.files.get('logo')

    if not data:
        abort(400, 'QR data required')
    if not HEX.match(fghex) or not HEX.match(bghex):
        abort(400, 'Invalid colour code')

    # optional logo
    logo = None
    if file and file.filename:
        try:
            logo = Image.open(file.stream).convert('RGBA')
        except Exception:
            abort(400, 'Invalid logo image')

    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(
        image_factory = StyledPilImage,
        module_drawer = drawer(style),
        color_mask    = SolidFillColorMask(
            front_color = hex_to_rgb(fghex),
            back_color  = hex_to_rgb(bghex)
        )
    ).convert('RGBA')

    # paste logo (optional)
    if logo:
        w, _ = qr_img.size
        L = int(w * 0.25)
        logo = logo.resize((L, L), Image.Resampling.LANCZOS)
        pad  = int(L * 0.08)
        bgL  = L + pad*2
        box  = Image.new('RGBA', (bgL, bgL), (255,255,255,255))
        box.paste(logo, (pad,pad), logo)
        pos = ((w-bgL)//2, (w-bgL)//2)
        qr_img.paste(box, pos, box)

    buf = BytesIO()
    qr_img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', download_name='qr_code.png')

@app.route('/history')
def history():
    return render_template('history.html')

@app.errorhandler(400)
def bad_request(e):
    return str(e), 400
@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)