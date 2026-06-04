"""
============================================================
  LIBRAS Bridge
  Arquivo: scripts/train_model.py
  Descricao: Coleta de dados e treinamento do classificador
             de sinais LIBRAS. Compativel com MediaPipe >= 0.10
             (Tasks API com hand_landmarker.task).

  USO:
    # Coletar amostras de um sinal:
    python scripts/train_model.py --collect --sign OI --samples 200

    # Treinar o modelo com os dados coletados:
    python scripts/train_model.py --train
============================================================
"""

import os
import pickle
import argparse
import time
import urllib.request
from typing import Optional

import cv2
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

DATA_DIR = "data/training"
MODELS_DIR = "models"
HAND_LANDMARKER_PATH = "models/hand_landmarker.task"
HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
MAX_HANDS = 2
TOTAL_FEATURES = MAX_HANDS * 21 * 3  # 126


def ensure_model_downloaded() -> bool:
    """Garante que o hand_landmarker.task esta disponivel localmente."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    if os.path.exists(HAND_LANDMARKER_PATH):
        return True
    print(f"Baixando modelo MediaPipe (~9 MB)...")
    try:
        def hook(b, bs, total):
            if total > 0:
                pct = min(b * bs * 100 / total, 100)
                print(f"\r  {pct:.0f}%", end="", flush=True)
        urllib.request.urlretrieve(HAND_LANDMARKER_URL, HAND_LANDMARKER_PATH, reporthook=hook)
        print("\nModelo baixado!")
        return True
    except Exception as e:
        print(f"\nErro ao baixar: {e}")
        return False


def build_landmarker():
    """Instancia o HandLandmarker da Tasks API."""
    import mediapipe as mp
    from mediapipe.tasks.python import vision
    from mediapipe.tasks.python.vision import HandLandmarker, HandLandmarkerOptions, RunningMode
    from mediapipe.tasks.python.core.base_options import BaseOptions

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_LANDMARKER_PATH),
        running_mode=RunningMode.IMAGE,
        num_hands=MAX_HANDS,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return HandLandmarker.create_from_options(options), mp


def extract_features(result, mp_module) -> Optional[np.ndarray]:
    """Extrai e normaliza landmarks de um HandLandmarkerResult."""
    if not result.hand_landmarks:
        return None

    all_features = []
    for hand_lms in result.hand_landmarks[:MAX_HANDS]:
        arr = np.array([[lm.x, lm.y, lm.z] for lm in hand_lms], dtype=np.float32)
        arr = arr - arr[0]                          # Normaliza pelo pulso
        mx = np.max(np.abs(arr))
        if mx > 0:
            arr /= mx
        all_features.append(arr.flatten())

    fv = np.concatenate(all_features)
    if len(fv) < TOTAL_FEATURES:
        fv = np.concatenate([fv, np.zeros(TOTAL_FEATURES - len(fv), dtype=np.float32)])
    return fv


def collect_data(sign_name: str, num_samples: int = 200) -> None:
    """Coleta amostras de um sinal LIBRAS usando a camera."""
    if not ensure_model_downloaded():
        print("Modelo nao disponivel. Verifique conexao com internet.")
        return

    sign_dir = os.path.join(DATA_DIR, sign_name.upper())
    os.makedirs(sign_dir, exist_ok=True)

    print(f"\n{'='*55}")
    print(f"COLETA: Sinal '{sign_name.upper()}' | {num_samples} amostras")
    print(f"{'='*55}")
    print("  [ESPACO] Iniciar/Pausar coleta")
    print("  [Q]      Encerrar\n")

    landmarker, mp_mod = build_landmarker()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERRO: camera nao encontrada!")
        return

    count = 0
    collecting = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp_mod.Image(image_format=mp_mod.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)

        if collecting and result.hand_landmarks:
            features = extract_features(result, mp_mod)
            if features is not None:
                np.save(os.path.join(sign_dir, f"sample_{count:04d}.npy"), features)
                count += 1
                print(f"\r  Amostras: {count}/{num_samples}", end="", flush=True)

        # Overlay de status
        color = (0, 255, 100) if collecting else (0, 200, 255)
        status = "COLETANDO..." if collecting else "PAUSADO (ESPACO)"
        cv2.putText(frame, f"Sinal: {sign_name.upper()}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, status, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        cv2.putText(frame, f"{count}/{num_samples}", (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        cv2.imshow(f"Coleta: {sign_name.upper()}", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord(" "):
            collecting = not collecting

        if count >= num_samples:
            print(f"\n\nConcluido! {count} amostras salvas.")
            time.sleep(1)
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


def train_model() -> None:
    """Carrega os dados coletados, treina e salva o melhor modelo."""
    print(f"\n{'='*55}")
    print("TREINAMENTO DO MODELO")
    print(f"{'='*55}")

    if not os.path.exists(DATA_DIR):
        print(f"Diretorio '{DATA_DIR}' nao encontrado.")
        print("Execute antes: python scripts/train_model.py --collect --sign NOME")
        return

    sign_dirs = [d for d in os.listdir(DATA_DIR)
                 if os.path.isdir(os.path.join(DATA_DIR, d))]

    if len(sign_dirs) < 2:
        print("E necessario ter dados de pelo menos 2 sinais diferentes.")
        return

    print(f"\nSinais encontrados: {sign_dirs}")
    X, y = [], []

    for sign in sign_dirs:
        files = [f for f in os.listdir(os.path.join(DATA_DIR, sign)) if f.endswith(".npy")]
        print(f"  {sign}: {len(files)} amostras")
        for fname in files:
            try:
                feat = np.load(os.path.join(DATA_DIR, sign, fname))
                X.append(feat)
                y.append(sign)
            except Exception:
                pass

    X, y = np.array(X), np.array(y)
    print(f"\nTotal: {len(X)} amostras | Shape: {X.shape}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    models = {
        "Random Forest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1))
        ]),
        "MLP": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", MLPClassifier(hidden_layer_sizes=(256, 128, 64),
                                  max_iter=500, random_state=42, early_stopping=True))
        ]),
        "SVM": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", C=10.0, gamma="scale", probability=True))
        ]),
    }

    best_model, best_acc, best_name = None, 0.0, ""

    for name, pipe in models.items():
        pipe.fit(X_train, y_train)
        acc = accuracy_score(y_test, pipe.predict(X_test))
        cv = cross_val_score(pipe, X, y, cv=5).mean()
        print(f"\n{name}: Teste={acc:.3f} | CV={cv:.3f}")
        print(classification_report(y_test, pipe.predict(X_test), target_names=sign_dirs))
        if acc > best_acc:
            best_acc, best_model, best_name = acc, pipe, name

    os.makedirs(MODELS_DIR, exist_ok=True)
    path = os.path.join(MODELS_DIR, "sign_classifier.pkl")
    with open(path, "wb") as f:
        pickle.dump({"model": best_model, "labels": sorted(sign_dirs),
                     "accuracy": best_acc, "model_name": best_name}, f)

    print(f"\nMelhor modelo: {best_name} ({best_acc*100:.1f}%)")
    print(f"Salvo em: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LIBRAS Bridge - Treinamento")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--sign", type=str, default="OI")
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--train", action="store_true")
    args = parser.parse_args()

    if args.collect:
        collect_data(args.sign, args.samples)
    elif args.train:
        train_model()
    else:
        parser.print_help()