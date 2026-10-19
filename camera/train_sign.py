"""Train the camera sign model (landmark features -> gloss) — same NumPy CNN family as the gloves.

    python camera/train_sign.py                               # camera/data, labels from ml/vocabulary.csv
    python camera/train_sign.py --val-user pragati            # hold one signer out: the honest number
    python camera/train_sign.py --folds 5                     # grouped CV (by signer if >= 3 signers)

  Transfer learning (recommended, see docs/training_guide.md):
    python camera/extract_videos.py INCLUDE/ camera/data_include          # landmarks from a public dataset
    python camera/train_sign.py --data camera/data_include --labels-from-data --out camera/models/pretrained.npz
    python camera/train_sign.py --init camera/models/pretrained.npz --reset-head --epochs 25 --lr 7e-4

  Personal fine-tune (5 takes per sign of the person who will use it):
    python camera/train_sign.py --data camera/data_manas --init camera/models/sign_model.npz --epochs 15 --lr 5e-4

Writes camera/models/sign_model.npz (+ camera/models/report.md). Needs numpy, scikit-learn.
"""
import argparse
import datetime
import os
import sys
import time

import numpy as np

from signdata import HERE, LAYERS, SEQ, augment, eval_windows, load_takes, load_vocab, vc


def train(takes, y, n_out, epochs, seed=0, lr=2e-3, init=None, reset_head=False, mirror=False, verbose=True):
    rng = np.random.default_rng(seed)
    xs = [t[3] for t in takes]
    if init is not None:
        mean, std = init["mean"], init["std"]
        p = {k: init[k].copy() for k in init if k[0] in "Wb"}
        if reset_head or p["bd"].shape[0] != n_out:
            q = vc.init_params(n_out, seed, n_in=len(mean), layers=LAYERS)
            p["Wd"], p["bd"] = q["Wd"], q["bd"]
    else:
        allx = np.concatenate(xs)
        mean, std = allx.mean(0), allx.std(0)
        std[std < 1e-3] = 1.0
        p = vc.init_params(n_out, seed, n_in=allx.shape[1], layers=LAYERS)
    counts = np.bincount(y, minlength=n_out).astype(float)
    cw = np.clip(np.where(counts > 0, counts.sum() / np.maximum(counts, 1) / n_out, 0), 0.3, 3.0)
    per = [max(2, (len(x) - SEQ) // 4 + 1) for x in xs]
    opt = vc.Adam(p, lr=lr, wd=3e-4)
    for ep in range(epochs):
        opt.lr = lr * 0.5 * (1 + np.cos(np.pi * ep / epochs)) + lr * 0.02
        idx = np.repeat(np.arange(len(xs)), per)
        rng.shuffle(idx)
        tot, t0 = 0.0, time.time()
        for b in range(0, len(idx), 64):
            ids = idx[b:b + 64]
            xb = np.stack([augment(xs[i], rng, mirror=mirror) for i in ids])
            probs, cache = vc.forward(p, mean, std, xb, train=True, drop=0.3, rng=rng, layers=LAYERS)
            loss, g = vc.backward(p, cache, probs, y[ids], n_out, smooth=0.1, class_w=cw)
            opt.step(p, g)
            tot += loss * len(ids)
        if verbose and (ep % 5 == 4 or ep == epochs - 1):
            print(f"  epoch {ep+1:3d}/{epochs}  loss {tot/len(idx):.3f}  ({time.time()-t0:.0f} s/epoch)")
    return p, mean, std


def evaluate(p, mean, std, takes, y):
    """Per-window top-1/top-3 and per-take (majority of windows) accuracy."""
    hits1 = hits3 = n = take_ok = 0
    preds = []
    for (_l, _u, _p, x), yy in zip(takes, y):
        w = eval_windows(x)
        pr = vc.predict_proba(p, mean, std, w, layers=LAYERS)
        top = np.argsort(-pr, axis=1)[:, :3]
        hits1 += (top[:, 0] == yy).sum()
        hits3 += (top == yy).any(1).sum()
        n += len(w)
        vote = np.bincount(top[:, 0], minlength=pr.shape[1]).argmax()
        take_ok += vote == yy
        preds.append(vote)
    return hits1 / n, hits3 / n, take_ok / len(takes), np.array(preds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "data"))
    ap.add_argument("--labels-from-data", action="store_true", help="every folder is a label (pretraining)")
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--folds", type=int, default=0)
    ap.add_argument("--val-user", default=None)
    ap.add_argument("--init", default=None, help="start from this model (transfer learning / fine-tuning)")
    ap.add_argument("--reset-head", action="store_true", help="new output layer (different label set)")
    ap.add_argument("--mirror", action="store_true", help="also learn left-handed versions")
    ap.add_argument("--out", default=os.path.join(HERE, "models", "sign_model.npz"))
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    vocab = load_vocab()
    say = dict(vocab)
    takes = load_takes(args.data, None if args.labels_from_data else set(say))
    if not takes:
        sys.exit(f"no takes in {args.data} - record some with camera/record.py")
    labels = sorted({t[0] for t in takes}) if args.labels_from_data else [l for l, _ in vocab if any(t[0] == l for t in takes)]
    if "REST" not in labels:
        print("warning: no REST takes - record hands-down / idle / scratching takes, or the decoder will over-trigger")
    li = {l: i for i, l in enumerate(labels)}
    y = np.array([li[t[0]] for t in takes])
    users = np.array([t[1] for t in takes])
    init = dict(np.load(args.init, allow_pickle=False)) if args.init else None
    print(f"{len(takes)} takes · {len(labels)} labels · signers: {', '.join(sorted(set(users)))}")

    lines = []
    if args.val_user or args.folds:
        from sklearn.model_selection import GroupKFold
        if args.val_user:
            splits = [(np.where(users != args.val_user)[0], np.where(users == args.val_user)[0])]
            name = f"held-out signer '{args.val_user}'"
        else:
            groups = users if len(set(users)) >= 3 else np.arange(len(takes))
            splits = list(GroupKFold(n_splits=min(args.folds, len(set(groups)))).split(y, y, groups))
            name = f"{len(splits)}-fold grouped by {'signer' if len(set(users)) >= 3 else 'take'}"
        r = []
        for k, (tr, te) in enumerate(splits):
            p, m, s = train([takes[i] for i in tr], y[tr], len(labels), args.epochs, args.seed + k, args.lr, init,
                            args.reset_head, args.mirror, verbose=False)
            a1, a3, at, _ = evaluate(p, m, s, [takes[i] for i in te], y[te])
            r.append((a1, a3, at))
            print(f"split {k+1}/{len(splits)}: window top-1 {a1:.1%} · top-3 {a3:.1%} · whole-take {at:.1%}")
        a1, a3, at = np.mean(r, axis=0)
        lines.append(f"| {name} | {a1:.1%} | {a3:.1%} | {at:.1%} |")

    print("training final model on all takes ...")
    p, mean, std = train(takes, y, len(labels), args.epochs, args.seed, args.lr, init, args.reset_head, args.mirror)
    info = (f"camera sign model · {len(takes)} takes · {len(labels)} labels · signers {len(set(users))} · "
            f"{datetime.date.today().isoformat()}")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    np.savez(args.out, mean=mean, std=std, labels=np.array(labels), say=np.array([say.get(l, l.lower()) for l in labels]),
             info=np.array(info), seq=np.array(SEQ), layers=np.array(LAYERS), **p)
    rep = os.path.join(os.path.dirname(args.out), "report.md")
    with open(rep, "w", encoding="utf-8") as f:
        f.write(f"# Camera sign model\n\n{info}\n\n| Validation | window top-1 | window top-3 | whole take |\n"
                f"|---|---|---|---|\n" + "\n".join(lines or ["| (none run) | | | |"]) + "\n")
    print(f"wrote {os.path.relpath(args.out)} and {os.path.relpath(rep)}")


if __name__ == "__main__":
    main()
