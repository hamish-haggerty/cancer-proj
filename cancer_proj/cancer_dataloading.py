# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/cancer_dataloading.ipynb.

# %% auto 0
__all__ = ['BYOL_Augs', 'TUNE_Augs', 'Val_Augs', 'process_path', 'extract_id', 'get_class_from_id', 'get_label_func_dict',
           'get_difference', 'get_fnames', 'save_dict_to_gdrive', 'load_dict_from_gdrive', 'DotDict', 'seed_everything',
           'get_resnet_encoder', 'create_model', 'create_aug_pipelines']

# %% ../nbs/cancer_dataloading.ipynb 4
import fastai
from fastai.vision.all import *
from base_rbt.base_model import * #probably don't need this whole thing...
from base_rbt.base_linear import show_linear_batch

# %% ../nbs/cancer_dataloading.ipynb 5
import re

def process_path(name):
    return name.as_posix().split('/')[-1] #basically get end part of Path('...') as a string

def extract_id(string):
    regex = r'ISIC_\d+'
    match = re.search(regex, string)
    if match:
        return match.group(0)
    else:
        return None

def get_class_from_id(string):
    "Given the identifier e.g. ISIC_0000000.jpg return the class label"

    row=data.loc[data['image'] == string]
    lst = [colname for colname in row.columns if row[colname].values==1]
    test_eq(len(lst),1)

    return lst[0]

def get_label_func_dict(_fnames):
    label_func_dict={}
    for name in _fnames:
        label_func_dict[name] = get_class_from_id(extract_id(process_path(name)))

    return label_func_dict

#label_func_dict = get_label_func_dict(_fnames) #can just load this in future to save time
#label_func_dict = data_dict['label_func_dict']

def get_difference(x1, x2):
    return list(set(x1) - set(x2))

#_labels = [label_func(x) for x in _fnames] 
#test_eq(len(_labels),len(_fnames))

# %% ../nbs/cancer_dataloading.ipynb 6
def get_fnames(_fnames):

    fnames_train=[]
    labels_train=[]
    count_dict={i:0 for i in set(_labels)}

    fnames = _fnames[0:5000]
    labels = _labels[0:5000]

    for i,lab in enumerate(labels):

        if count_dict[lab]<500:
            fnames_train.append(_fnames[i])
            labels_train.append(_labels[i])

        count_dict[lab]+=1

    fnames_valid = _fnames[5000:5000+256*5]
    labels_valid = _labels[5000:5000+256*5]

    fnames_test = get_difference(_fnames,fnames_train+fnames_valid)
    fnames_test.sort()
    labels_test = [label_func(path) for path in fnames_test]

   
    return {'fnames_train':fnames_train,'fnames_valid':fnames_valid,'fnames_test':fnames_test,
            'labels_train':labels_train,'labels_valid':labels_valid,'labels_test':labels_test
           }


# %% ../nbs/cancer_dataloading.ipynb 9
import pickle

def save_dict_to_gdrive(d,directory, filename):
    #e.g. directory='/content/drive/My Drive/random_initial_weights'
    filepath = directory + '/' + filename + '.pkl'
    with open(filepath, "wb") as f:
        pickle.dump(d, f)

def load_dict_from_gdrive(directory,filename):
    #e.g. directory='/content/drive/My Drive/random_initial_weights'
    filepath = directory + '/' + filename + '.pkl'
    with open(filepath, "rb") as f:
        d = pickle.load(f)
    return d

# %% ../nbs/cancer_dataloading.ipynb 10
class DotDict(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

# %% ../nbs/cancer_dataloading.ipynb 11
def seed_everything(TORCH_SEED):
    random.seed(TORCH_SEED)
    os.environ['PYTHONHASHSEED'] = str(TORCH_SEED)
    np.random.seed(TORCH_SEED)
    torch.manual_seed(TORCH_SEED)
    torch.cuda.manual_seed_all(TORCH_SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# %% ../nbs/cancer_dataloading.ipynb 12
@torch.no_grad()
def get_resnet_encoder(model,n_in=3):
    model = create_body(model, n_in=n_in, pretrained=False, cut=len(list(model.children()))-1)
    model.add_module('flatten', torch.nn.Flatten())
    return model

@torch.no_grad()
def create_model(which_model,device,ps=8192,n_in=3):

    #pretrained=True if 'which_model' in ['bt_pretrain', 'supervised_pretrain'] else False

    if which_model == 'bt_pretrain': model = torch.hub.load('facebookresearch/barlowtwins:main', 'resnet50')
    
    elif which_model == 'no_pretrain': model = resnet50()

    elif which_model == 'supervised_pretrain': model = resnet50(weights='IMAGENET1K_V2')

    #ignore the 'pretrained=False' argument here. Just means we use the weights above 
    #(which themselves are either pretrained or not)
    encoder = get_resnet_encoder(model)

    model = create_barlow_twins_model(encoder, hidden_size=ps,projection_size=ps,nlayers=3)

    if device == 'cuda':
        model.cuda()
        encoder.cuda()


    return model,encoder

# %% ../nbs/cancer_dataloading.ipynb 14
BYOL_Augs = dict(flip_p1=0.5,flip_p2=0.5,jitter_p1=0.8,jitter_p2=0.8,bw_p1=0.2,
                bw_p2=0.2,blur_p1=1.0,blur_p2=0.1,sol_p1=0.0,sol_p2=0.2,noise_p1=0.0,
                noise_p2=0.0,resize_scale=(0.7, 1.0),resize_ratio=(3/4, 4/3),rotate_deg=45.0,
                rotate_p=0.5,blur_r=(0.1,2),blur_s=13,sol_t=0.1,sol_a=0.1,noise_std=0.1 
                )


TUNE_Augs=dict(blur_r = BYOL_Augs['blur_r'],blur_s = BYOL_Augs['blur_s'], flip_p=0.25,
                rotate_p=0.25,jitter_p=0.0,bw_p=0.0,blur_p=0.0,resize_scale=(0.7, 1.0),
                resize_ratio=(3/4, 4/3),rotate_deg=45.0
                )

Val_Augs = dict(TUNE_Augs)


def create_aug_pipelines(size,device,Augs=BYOL_Augs,TUNE_Augs=TUNE_Augs,Val_Augs=Val_Augs):
    "Create the BT pipelines, the tune and val pipelines"

    aug_dict = {}

    aug_pipelines_1 = get_barlow_twins_aug_pipelines(size=size,
                        rotate=True,jitter=True,noise=True,bw=True,blur=True,solar=True, #Whether to use aug or not
                        resize_scale=Augs['resize_scale'],resize_ratio=Augs['resize_ratio'],
                        noise_std=Augs['noise_std'], rotate_deg=Augs['rotate_deg'],
                        blur_r=Augs['blur_r'],blur_s=Augs['blur_s'],sol_t=Augs['sol_t'],sol_a=Augs['sol_a'],
                        flip_p=Augs['flip_p1'], rotate_p=Augs['rotate_p'],noise_p=Augs['noise_p1'],
                        jitter_p=Augs['jitter_p1'], bw_p=Augs['bw_p1'], blur_p=Augs['blur_p1'],
                        sol_p=Augs['sol_p1'], #prob of performing aug
                        same_on_batch=False,stats=None, cuda=(device=='cuda'))

    aug_pipelines_2 = get_barlow_twins_aug_pipelines(size=size,
                        rotate=True,jitter=True,noise=True,bw=True,blur=True,solar=True, #Whether to use aug or not
                        resize_scale=Augs['resize_scale'],resize_ratio=Augs['resize_ratio'],
                        noise_std=Augs['noise_std'], rotate_deg=Augs['rotate_deg'],
                        blur_r=Augs['blur_r'],blur_s=Augs['blur_s'],sol_t=Augs['sol_t'],sol_a=Augs['sol_a'],
                        flip_p=Augs['flip_p2'], rotate_p=Augs['rotate_p'],noise_p=Augs['noise_p2'],
                        jitter_p=Augs['jitter_p2'], bw_p=Augs['bw_p2'], blur_p=Augs['blur_p2'],
                        sol_p=Augs['sol_p2'], #prob of performing aug
                        same_on_batch=False,stats=None, cuda=(device=='cuda'))

    aug_pipelines = [aug_pipelines_1,aug_pipelines_2]


    aug_pipelines_tune =  [get_barlow_twins_aug_pipelines(size=size,
                    rotate=True,jitter=True,noise=False,bw=True,blur=True,solar=False, #Whether to use aug or not
                    resize_scale=TUNE_Augs['resize_scale'],resize_ratio=TUNE_Augs['resize_ratio'],noise_std=None,
                    blur_r=TUNE_Augs['blur_r'],blur_s=TUNE_Augs['blur_s'], rotate_deg=TUNE_Augs['rotate_deg'],
                    sol_t=None,sol_a=None, #hps of augs
                    flip_p=TUNE_Augs['flip_p'], rotate_p=TUNE_Augs['rotate_p'],noise_p=0.0, jitter_p=TUNE_Augs['jitter_p'],
                    bw_p=TUNE_Augs['bw_p'], blur_p=TUNE_Augs['blur_p'],sol_p=0.0, #prob of performing aug
                    same_on_batch=False,stats=None, cuda=(device=='cuda'))]#,P=0.0)




    aug_pipelines_test =  [get_barlow_twins_aug_pipelines(size=size,
                    rotate=True,jitter=True,noise=False,bw=True,blur=True,solar=False, #Whether to use aug or not
                    resize_scale=Val_Augs['resize_scale'],resize_ratio=Val_Augs['resize_ratio'],noise_std=None,
                    blur_r=Val_Augs['blur_r'],blur_s=Val_Augs['blur_s'], rotate_deg=Val_Augs['rotate_deg'],
                    sol_t=None,sol_a=None, #hps of augs
                    flip_p=Val_Augs['flip_p'], rotate_p=Val_Augs['rotate_p'],noise_p=0.0, jitter_p=Val_Augs['jitter_p'],
                    bw_p=Val_Augs['bw_p'], blur_p=Val_Augs['blur_p'],sol_p=0.0, #prob of performing aug
                    same_on_batch=False,stats=None, cuda=(device=='cuda'))]#,P=0.0)

    aug_dict['aug_pipelines'] = aug_pipelines
    aug_dict['aug_pipelines_tune'] = aug_pipelines_tune
    aug_dict['aug_pipelines_test'] = aug_pipelines_test

    return aug_dict


