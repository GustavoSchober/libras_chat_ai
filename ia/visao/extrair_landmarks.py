"""Extrai landmarks holísticos (pose 33, mãos 21+21, face blendshapes) de cada vídeo → .npz

Ambiente separado (o mediapipe não tem wheel para o Python do sistema):
  uv venv -p 3.12 .venv-visao && uv pip install -p .venv-visao/bin/python mediapipe numpy numba
  curl -sSLo holistic.task https://storage.googleapis.com/mediapipe-models/holistic_landmarker/holistic_landmarker/float16/latest/holistic_landmarker.task
  .venv-visao/bin/python ia/visao/extrair_landmarks.py <pasta_videos> <pasta_saida> holistic.task

Precisa de ffmpeg/ffprobe. 8 processos: ~100 quadros/s (90 vídeos do V-LIBRASIL em ~3 min).
Ver KNOWLEDGE/15.
"""
import sys, os, numpy as np, mediapipe as mp
from mediapipe.tasks.python import vision, BaseOptions
from concurrent.futures import ProcessPoolExecutor

def um(args):
    video, out, modelo = args
    if os.path.exists(out): return out, 0
    opt = vision.HolisticLandmarkerOptions(base_options=BaseOptions(model_asset_path=modelo),
            running_mode=vision.RunningMode.VIDEO, output_face_blendshapes=True)
    lm = vision.HolisticLandmarker.create_from_options(opt)
    # OpenCV devolve quadros PRETOS nos vídeos entrelaçados do V-LIBRASIL: ffmpeg + yadif
    import subprocess, json as _j
    info = _j.loads(subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
        "stream=width,height,r_frame_rate","-of","json",video],capture_output=True,text=True).stdout)["streams"][0]
    W = 960; H = round(info["height"] * W / info["width"] / 2) * 2
    a, b = info["r_frame_rate"].split("/"); fps = float(a) / float(b)
    pipe = subprocess.Popen(["ffmpeg","-v","error","-i",video,"-vf",f"yadif,scale={W}:{H}","-f","rawvideo",
        "-pix_fmt","rgb24","-"], stdout=subprocess.PIPE)
    P, L, R, B = [], [], [], []; i = 0
    nan = lambda n: np.full((n, 3), np.nan, np.float32)
    arr = lambda pts: np.array([[p.x, p.y, p.z] for p in pts], np.float32)
    while True:
        buf = pipe.stdout.read(W * H * 3)
        if len(buf) < W * H * 3: break
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy())
        r = lm.detect_for_video(img, int(i * 1000 / fps)); i += 1
        P.append(arr(r.pose_landmarks) if r.pose_landmarks else nan(33))
        L.append(arr(r.left_hand_landmarks) if r.left_hand_landmarks else nan(21))
        R.append(arr(r.right_hand_landmarks) if r.right_hand_landmarks else nan(21))
        B.append(np.array([c.score for c in r.face_blendshapes], np.float32) if r.face_blendshapes else np.full(52, np.nan, np.float32))
    np.savez_compressed(out, pose=np.stack(P), esq=np.stack(L), dir=np.stack(R), bs=np.stack(B), fps=fps,
                        wh=np.array([W, H]))
    return out, i

if __name__ == "__main__":
    vids, outdir, modelo = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    jobs = [(os.path.join(vids, v), os.path.join(outdir, v[:-4] + ".npz"), modelo) for v in sorted(os.listdir(vids))]
    import time; t = time.time(); n = 0
    with ProcessPoolExecutor(8) as ex:
        for out, k in ex.map(um, jobs): n += k
    print(f"{len(jobs)} vídeos, {n} quadros, {time.time()-t:.0f} s")
