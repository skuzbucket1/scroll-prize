"""Synthetic Greek letters painted into real papyrus renders (2026-10-13, idea 2; Ted: "start on number 2"). The 8.64 µm
fine-tune on 12 of Nieuwlaar's letters failed for two reasons: too few letters, and labels made by our own models. Here
the labels are exact (we paint them) and unlimited, and the papyrus is the target scans' own: text-free windings of
PHerc0813 / PHerc0191 (9.362 µm). What we paint is the part that must be right. The ablations on PHerc0841's real
letters say the models read fine texture (about 75 µm) in the layers just above the surface, not brightness, so the ink
effect is a texture change with per-layer weights, set from texture_signature.py's measurements (experiments/ink-ablation).

Pieces:
  letter_mask(H, W, um, rng)  a stroke mask (float 0..1) of 1-4 lines of Greek capitals: DejaVu Sans / Serif glyphs,
                              letter height 2.0-3.0 mm, stroke width set to 0.25-0.45 mm by erosion / dilation, line
                              spacing 4.5-6 mm, small rotations, shear and an elastic warp, broken and faded strokes
                              (abraded ink), blurred by a 1.5 px PSF. Returns the mask and the letter boxes.
  paint(ct, valid, mask, eff) the 66-layer render with the ink effect applied inside the mask:
                              eff = {"layers": {"30": w, ...}, "smooth": a, "sigma_um": s, "bright": b, "stripes": c}
                              smooth: blend each weighted layer toward its Gaussian (sigma_um) by a * w * mask
                                      (ink filling the gaps between fibres flattens the fine texture);
                              bright: add b * w * mask (CT units; 0 at 9.36 µm per the de-weave test, kept for 8.64 µm);
                              stripes: damp the horizontal-stripe (fibre) component, I - G_x-long(I), by c * w * mask.
  dataset                     loops text-free windings: random letter blocks on valid papyrus (no more than ~15 % of
                              the area), paints, writes villa's flat layout (surface-volume.zarr = layers 65..1 reversed,
                              as model-8um-v1's build_dataset.py, so plane 32 = layer 33 and the reading side is the
                              stored order the models are trained in), ink labels = mask > 0.5, supervision = valid area,
                              validation = the last 15 % of each winding's length.
Usage: synth_letters.py preview <render.zarr> <um> <effect.json> <out.jpg> [--seed 0]
       synth_letters.py dataset <effect.json> <out dir> <um> <render.zarr> [<render.zarr> ...] [--seed 0] [--blocks 4]"""
import json, os, sys
import cv2, numpy as np, zarr

GREEK = 'ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ' + 'ΑΕΙΟΝΣΤΗΚΛΜΠΡ' * 2           # common letters more often, as in Greek prose
FONTS = ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
         '/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf']


def glyph(ch, px, font):
    """Binary image of one capital, cap height about `px` pixels, tightly cropped."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(font, int(px * 1.4))
    im = Image.new('L', (int(px * 2.2), int(px * 2.2)), 0); ImageDraw.Draw(im).text((int(px * 0.3), 0), ch, fill=255, font=f)
    a = np.asarray(im) > 127; ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1] if len(ys) else np.zeros((1, 1), bool)


def stroke_width(g, target_px):
    """Erode / dilate a glyph so that its strokes are about target_px wide (median of twice the distance transform)."""
    d = cv2.distanceTransform(g.astype(np.uint8), cv2.DIST_L2, 3)
    cur = 2 * float(np.median(d[d > 0])) if (d > 0).any() else target_px
    k = int(round(abs(target_px - cur) / 2))
    if k == 0:
        return g
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    return (cv2.dilate if target_px > cur else cv2.erode)(g.astype(np.uint8), se) > 0


def letter_mask(H, W, um, rng, lines=None):
    mm = 1000. / um; M = np.zeros((H, W), np.float32); boxes = []
    lh = rng.uniform(2.0, 3.0) * mm; sw = rng.uniform(0.25, 0.45) * mm; ls = rng.uniform(4.5, 6.0) * mm
    nl = lines or int(rng.integers(1, 5)); y = rng.uniform(0.6, 1.2) * mm + lh
    font = FONTS[int(rng.integers(len(FONTS)))]
    for _ in range(nl):
        if y > H - 0.3 * mm:
            break
        x = rng.uniform(0.3, 1.5) * mm
        while x < W - lh:
            ch = GREEK[int(rng.integers(len(GREEK)))]
            g = stroke_width(glyph(ch, lh * rng.uniform(0.9, 1.1), font), sw * rng.uniform(0.85, 1.15))
            gh, gw = g.shape; pad = int(0.3 * lh); g = np.pad(g.astype(np.float32), pad)
            ang = rng.uniform(-4, 4); sh = rng.uniform(-0.12, 0.12)              # small rotation and slant
            A = cv2.getRotationMatrix2D((g.shape[1] / 2, g.shape[0] / 2), ang, 1.0); A[0, 1] += sh; A[0, 2] -= sh * g.shape[0] / 2
            g = cv2.warpAffine(g, A, (g.shape[1], g.shape[0]), flags=cv2.INTER_LINEAR)
            y0 = int(y - g.shape[0] + pad + rng.normal(0, 0.05 * lh)); x0 = int(x)
            ya, yb, xa, xb = max(0, y0), min(H, y0 + g.shape[0]), max(0, x0), min(W, x0 + g.shape[1])
            if yb > ya and xb > xa:
                M[ya:yb, xa:xb] = np.maximum(M[ya:yb, xa:xb], g[ya - y0:yb - y0, xa - x0:xb - x0])
                boxes.append([xa, ya, xb, yb])
            x += gw + rng.uniform(0.25, 0.7) * mm
        y += ls
    if not boxes:
        return M, boxes
    # elastic warp (wobbly pen), broken strokes and fading (abraded ink), PSF
    s = max(H, W) / 6; dx = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), s) * 6 * s / 3
    dy = cv2.GaussianBlur(rng.normal(0, 1, (H, W)).astype(np.float32), (0, 0), s) * 6 * s / 3
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    M = cv2.remap(M, gx + dx * 0.02 * mm, gy + dy * 0.02 * mm, cv2.INTER_LINEAR)
    holes = cv2.GaussianBlur(rng.random((H, W)).astype(np.float32), (0, 0), 0.08 * mm)
    holes = (holes - holes.mean()) / (holes.std() + 1e-6)
    M *= np.clip(1.4 + holes, 0, 1)                                         # gaps where the field dips
    fade = cv2.GaussianBlur(rng.random((H, W)).astype(np.float32), (0, 0), 1.0 * mm)
    M *= np.clip(0.55 + (fade - fade.mean()) / (fade.std() + 1e-6) * 0.25, 0.2, 1.0)
    M = cv2.GaussianBlur(M, (0, 0), 1.5)
    return np.clip(M, 0, 1), boxes


def paint(ct, valid, M, eff, um):
    """ct: (66, H, W) uint8. Returns a painted copy (uint8)."""
    out = ct.astype(np.float32).copy(); m = M * valid
    sig = eff.get('sigma_um', 40) / um; a, b, c = eff.get('smooth', 0.0), eff.get('bright', 0.0), eff.get('stripes', 0.0)
    for ls, w in eff['layers'].items():
        k = int(ls); I = out[k]
        if a:
            I = I - a * w * m * (I - cv2.GaussianBlur(I, (0, 0), sig))
        if c:
            lx = cv2.blur(I, (int(round(600 / um)) | 1, 1))                     # 0.6 mm along the winding: the fibres
            I = I - c * w * m * (lx - cv2.GaussianBlur(lx, (0, 0), 2 * sig))
        if b:
            I = I + b * w * m
        out[k] = I
    out = np.clip(np.round(out), 1, 255).astype(np.uint8); out[ct == 0] = 0
    return out


def preview(args):
    rp, um, effp, outp = args[0], float(args[1]), args[2], args[3]
    seed = int(args[args.index('--seed') + 1]) if '--seed' in args else 0; rng = np.random.default_rng(seed)
    eff = json.load(open(effp)); R = zarr.open(rp, mode='r')['0']; H, W = R.shape[1:]
    y0, x0 = H // 2 - min(H, 1200) // 2, W // 2 - 1600; h, w = min(H, 1200), 3200
    ct = np.asarray(R[:, y0:y0 + h, x0:x0 + w]); valid = (ct > 0).all(0)
    M, boxes = letter_mask(h, w, um, rng); P = paint(ct, valid, M, eff, um)
    k = max(int(l) for l in eff['layers'])
    tiles = []
    for name, img in (('original', ct[k]), ('painted', P[k]), ('difference x4', np.clip(128 + 4 * (P[k].astype(np.int16) - ct[k]), 0, 255).astype(np.uint8)),
                      ('mask', (M * 255).astype(np.uint8))):
        g = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR); g = cv2.resize(g, (w // 2, h // 2), interpolation=cv2.INTER_AREA)
        cv2.putText(g, f'{name} (layer {k})', (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA); tiles.append(g)
    cv2.imwrite(outp, np.concatenate(tiles, 0), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print('written', outp, len(boxes), 'letters')


def dataset(args):
    effp, out, um = args[0], args[1], float(args[2]); rest = args[3:]
    seed = int(rest[rest.index('--seed') + 1]) if '--seed' in rest else 0
    nb = int(rest[rest.index('--blocks') + 1]) if '--blocks' in rest else 4
    renders = [r for r in rest if r.endswith('.zarr')]; rng = np.random.default_rng(seed); eff = json.load(open(effp))
    os.makedirs(out, exist_ok=True)
    for rp in renders:
        name = 'synth-' + os.path.basename(rp)[:-5]; d = os.path.join(out, name); os.makedirs(d, exist_ok=True)
        ct = np.asarray(zarr.open(rp, mode='r')['0']); H, W = ct.shape[1:]; valid = (ct[25:42] > 0).all(0)
        M = np.zeros((H, W), np.float32); bh, bw = int(9 * 1000 / um), int(25 * 1000 / um)
        for _ in range(nb * 4):
            if (M > 0.5).sum() > 0.15 * valid.sum():
                break
            y, x = int(rng.integers(0, max(1, H - bh))), int(rng.integers(0, max(1, int(W * 0.85) - bw)))
            if valid[y:y + bh, x:x + bw].mean() < 0.85:
                continue
            m, _ = letter_mask(bh, bw, um, rng); M[y:y + bh, x:x + bw] = np.maximum(M[y:y + bh, x:x + bw], m)
        P = paint(ct, valid, M, eff, um)
        vol = P[1:66][::-1].copy()
        g = zarr.open_group(os.path.join(d, 'surface-volume.zarr'), mode='w', zarr_format=2)
        g.create_array('0', shape=vol.shape, chunks=(8, 128, 128), dtype='u1', fill_value=0)[:] = vol
        val = np.zeros((H, W), bool); val[:, int(W * 0.85):] = True
        for k, msk in (('inklabels', (M > 0.5) & valid), ('supervision_mask', valid), ('validation_mask', val & valid)):
            cv2.imwrite(os.path.join(d, f'{name}_{k}.png'), msk.astype(np.uint8) * 255)
        print(f'{name}: ink {(M > 0.5).sum() / max(valid.sum(), 1):.1%} of the valid area', flush=True)
    json.dump(dict(effect=eff, um=um, seed=seed, renders=renders), open(os.path.join(out, 'synth_config.json'), 'w'), indent=1)


if __name__ == '__main__':
    a = sys.argv[1:]
    {'preview': preview, 'dataset': dataset}[a[0]](a[1:])
