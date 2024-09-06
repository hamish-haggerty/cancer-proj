cancer-proj
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

Update: This is mostly superseded by `base_rbt` and upcoming arxiv paper.

Package implementing results for masters thesis at UNSW and accompanying
paper (please see:
[Publications](https://hamish-haggerty.github.io/publications/)).
Comparison of supervised transfer learning vs. self-supervised transfer
learning on cancer image dataset (ISIC) with limited labelled data.

Keywords: Barlow Twins, 1cycle policy, transfer learning, cancer image
classification, skin cancer, low labelled data

## Install

``` sh
pip install git+https://github.com/hamish-haggerty/cancer-proj.git
```

## How to use

Full documentation and code examples are upcoming. For now, easiest way
to use code is to open `experiments/cancer_results.ipynb` in Colab. You
will need to download the dataset and save it to your google drive to
use that notebook code as is (see start of notebook for details on
dataset).

Transfer learning can be done by a single call to
[`main_tune`](https://hamish-haggerty.github.io/cancer-proj/cancer_maintrain.html#main_tune)
function, once several variables have been defined, including the
initial weights, dataloaders, augmentation pipelines, etc. This is all
clear in `cancer_results` notebook.

In `experiments/bt_cancer_results` we also implement what we call
`pre-pretraining.` This means we pretrain with Barlow Twins on the
target data, using an already pretrained network (on ImageNet, with
Barlow Twins) as the starting weights. This network is then fine tuned.
The `pre-pretraining` involves reinitialising a projector network, and
freezing the pretrained encoder while the projector only is updated for
several epochs. In other words, we use transfer learning but in a
self-supervised manner. The code can be used as a black box without
understanding these details however (or, see upcoming paper).
