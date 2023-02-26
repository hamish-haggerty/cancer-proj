# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/cancer_dataloading.ipynb.

# %% auto 0
__all__ = ['colab_train_dir', 'colab_test_dir', 'local_train_dir', 'local_test_dir', 'melanoma_names_train',
           'actinickeratosis_names_valid', 'BYOL_Augs', 'TUNE_Augs', 'Val_Augs', 'get_file_lists', 'extract_text',
           'label_func', 'get_difference', 'get_fnames_dict', 'get_data_dict', 'get_fnames_dls_dict',
           'save_dict_to_gdrive', 'load_dict_from_gdrive', 'tensor_to_np', 'seed_everything', 'test_fnames',
           'get_resnet_encoder', 'create_model', 'create_aug_pipelines']

# %% ../nbs/cancer_dataloading.ipynb 5
import fastai
from fastai.vision.all import *
from base_rbt.base_model import * #probably don't need this whole thing...
from base_rbt.base_linear import show_linear_batch

# %% ../nbs/cancer_dataloading.ipynb 6
#colab
colab_train_dir='skin_cancer_ISIC/Train'
colab_test_dir='skin_cancer_ISIC/Test'

# %% ../nbs/cancer_dataloading.ipynb 7
#local
local_train_dir='/Users/hamishhaggerty/Downloads/skin_cancer_ISIC/Train'
local_test_dir='/Users/hamishhaggerty/Downloads/skin_cancer_ISIC/Test'

# %% ../nbs/cancer_dataloading.ipynb 9
#Seems all we need here is class_names?

def get_file_lists(train_dir):

    #train
    class_names0 = os.listdir(train_dir)
    class_names = sorted(class_names0)
    num_class = len(class_names)
    image_files = [[os.path.join(train_dir, class_name, x) 
                for x in os.listdir(os.path.join(train_dir, class_name))] 
                for class_name in class_names]

    image_file_list = []
    image_label_list = []
    for i, class_name in enumerate(class_names):
        image_file_list.extend(image_files[i])
        image_label_list.extend([i] * len(image_files[i]))
    num_total = len(image_label_list)

    return {'image_file_list':image_file_list, 'image_label_list':image_label_list, 'num_total':num_total, 'num_class':num_class, 'class_names':class_names}


# %% ../nbs/cancer_dataloading.ipynb 10
#Helper functions to extract class names from the filenames
import re
def extract_text(string):
    # Use the compile method to create a RegexObject
    pattern = re.compile(r'/Train/(.*?)/ISIC')

    # Use the search method of the RegexObject to find the pattern in the string
    match = pattern.search(string)

    # If a match is found, return the matched text
    if match:
        return match.group(1)
    # If no match is found, return None
    else:
        
        return None

def label_func(x): return extract_text(x.as_posix())

def get_difference(x1, x2):
    return list(set(x1) - set(x2))


# %% ../nbs/cancer_dataloading.ipynb 11
def get_fnames_dict(train_dir,test_dir,class_names):
    "get dictionary of fnames"

        #files names
    fnames = get_image_files(train_dir)
    fnames.sort()

    #Extract training set
    max_num =100 #maximum number of samples in each class
    count_dict = {i:0 for i in class_names}
    fnames_train = []
    for i in fnames:
        #st=extract_text(i.as_posix())
        st=label_func(i)
        
        if count_dict[st]<max_num: #no more than 100 samples per category
            fnames_train.append(i)
            count_dict[st]+=1
                    
    #We further partition fnames_train into a tune-valiation set
    count_dict2 = {i:0 for i in class_names}
    fnames_tune = []
    for i in fnames_train:
        st = label_func(i)
        if count_dict2[st] < 0.8*count_dict[st]:
            fnames_tune.append(i)
            count_dict2[st]+=1
            
    fnames_tune.sort()
            

    fnames_valid = get_difference(fnames_train,fnames_tune)
    fnames_valid.sort()

    fnames_test = get_difference(fnames,fnames_train) + get_image_files(test_dir)
    fnames_test.sort()
    
    fnames_train = fnames_tune
    
    
    return {'fnames':fnames,'fnames_train':fnames_train,'fnames_tune':fnames_tune,
            'fnames_valid':fnames_valid,
            'fnames_test':fnames_test
            }


# %% ../nbs/cancer_dataloading.ipynb 12
def get_data_dict(fnames_dict,train_dir,test_dir, #basic stuff needed
                  device,bs_val,bs=256,bs_tune=256,size=128,n_in=3 #hyperparameters
                 ):
        "get dictionary of data"

        #fnames = fnames_dict['fnames']
        fnames_train = fnames_dict['fnames_train']
        fnames_tune = fnames_dict['fnames_tune']
        fnames_valid = fnames_dict['fnames_valid']
        #fnames_test = fnames_dict['fnames_test']

        item_tfms = [Resize(size)]

        dls_train  = ImageDataLoaders.from_path_func(train_dir, fnames_train, label_func,
                                        bs=bs,
                                        item_tfms=item_tfms,
                                        valid_pct=0,
                                        device=device,
                                        num_workers=12*(device=='cuda')
                                        )
        x,y = dls_train.one_batch()

        dls_tune = ImageDataLoaders.from_path_func(train_dir, fnames_tune, label_func,
                                        bs=bs_tune,
                                        item_tfms=item_tfms,
                                        valid_pct=0,
                                        device=device,
                                        shuffle=True,
                                        num_workers=12*(device=='cuda'),
                                        )
        xtune,ytune = dls_tune.one_batch()

        dls_valid  = ImageDataLoaders.from_path_func(train_dir, fnames_valid, label_func,
                                        bs=bs_val,
                                        item_tfms=item_tfms,
                                        valid_pct=0,
                                        num_workers=12*(device=='cuda')
                                        )
        
        xval,yval = dls_valid.one_batch()

        vocab = dls_valid.vocab

        #return the dls etc
        return {'dls_train':dls_train,'dls_tune':dls_tune,'dls_valid':dls_valid,
                'x':x,'y':y,'xval':xval,'yval':yval,'xtune':xtune,'ytune':ytune,
                'vocab':vocab
                }


# %% ../nbs/cancer_dataloading.ipynb 13
def get_fnames_dls_dict(train_dir,test_dir,
                        device,bs_val,bs=256,bs_tune=256,size=128,n_in=3,
                        ):

    "Wrapper that returns a dictionary with the fnames, dls etc"

    #do stuff

    class_names = get_file_lists(train_dir)['class_names']
    
    fnames_dict = get_fnames_dict(train_dir,test_dir,class_names)

    data_dict = get_data_dict(fnames_dict,train_dir,test_dir, #basic stuff needed
                  device,bs_val,bs=bs,bs_tune=bs_tune,size=size,n_in=n_in #hyperparameters
                 )

    d = {**fnames_dict,**data_dict}
    
    return d


# %% ../nbs/cancer_dataloading.ipynb 14
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

# %% ../nbs/cancer_dataloading.ipynb 15
import numpy as np

def tensor_to_np(tensor_image):
    return tensor_image.cpu().numpy()

# %% ../nbs/cancer_dataloading.ipynb 16
def seed_everything(TORCH_SEED):
    random.seed(TORCH_SEED)
    os.environ['PYTHONHASHSEED'] = str(TORCH_SEED)
    np.random.seed(TORCH_SEED)
    torch.manual_seed(TORCH_SEED)
    torch.cuda.manual_seed_all(TORCH_SEED)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

# %% ../nbs/cancer_dataloading.ipynb 20
#So we can check that e.g. loading on colab will give the same results

def test_fnames(_fnames):
    melanoma_names=[]
    basalcellcarcinoma_names=[]
    actinickeratosis_names=[]

    for i in _fnames:

        if 'melanoma' in i.as_posix(): melanoma_names.append(i.as_posix().split('/')[-1])

        if 'basal cell carcinoma' in i.as_posix(): basalcellcarcinoma_names.append(i.as_posix().split('/')[-1])

        if 'actinic keratosis' in i.as_posix(): actinickeratosis_names.append(i.as_posix().split('/')[-1])
    
    return melanoma_names,basalcellcarcinoma_names,actinickeratosis_names


# %% ../nbs/cancer_dataloading.ipynb 21
melanoma_names_train=['ISIC_0000139.jpg','ISIC_0000141.jpg','ISIC_0000142.jpg','ISIC_0000143.jpg','ISIC_0000144.jpg','ISIC_0000145.jpg','ISIC_0000146.jpg','ISIC_0000147.jpg','ISIC_0000148.jpg','ISIC_0000149.jpg','ISIC_0000150.jpg','ISIC_0000151.jpg','ISIC_0000152.jpg','ISIC_0000153.jpg','ISIC_0000154.jpg','ISIC_0000155.jpg','ISIC_0000156.jpg','ISIC_0000157.jpg','ISIC_0000158.jpg','ISIC_0000159.jpg','ISIC_0000160.jpg','ISIC_0000161.jpg','ISIC_0000162.jpg','ISIC_0000163.jpg','ISIC_0000164.jpg','ISIC_0000165.jpg','ISIC_0000166.jpg','ISIC_0000167.jpg','ISIC_0000168.jpg','ISIC_0000169.jpg','ISIC_0000170.jpg','ISIC_0000171.jpg','ISIC_0000172.jpg','ISIC_0000173.jpg','ISIC_0000174.jpg','ISIC_0000175.jpg','ISIC_0000176.jpg','ISIC_0000278.jpg','ISIC_0000279.jpg','ISIC_0000280.jpg','ISIC_0000285.jpg','ISIC_0000288.jpg','ISIC_0000289.jpg','ISIC_0000291.jpg','ISIC_0000292.jpg','ISIC_0000293.jpg','ISIC_0000294.jpg','ISIC_0000295.jpg','ISIC_0000296.jpg','ISIC_0000297.jpg','ISIC_0000298.jpg','ISIC_0000299.jpg','ISIC_0000300.jpg','ISIC_0000301.jpg','ISIC_0000302.jpg','ISIC_0000303.jpg','ISIC_0000304.jpg','ISIC_0000305.jpg','ISIC_0000306.jpg','ISIC_0000307.jpg','ISIC_0000308.jpg','ISIC_0000309.jpg','ISIC_0000310.jpg','ISIC_0000311.jpg','ISIC_0000312.jpg','ISIC_0000313.jpg','ISIC_0000314.jpg','ISIC_0000390.jpg','ISIC_0000393.jpg','ISIC_0000394.jpg','ISIC_0000395.jpg','ISIC_0000398.jpg','ISIC_0000399.jpg','ISIC_0000400.jpg','ISIC_0000401.jpg','ISIC_0000402.jpg','ISIC_0000404.jpg','ISIC_0000405.jpg','ISIC_0000406.jpg','ISIC_0000410.jpg']

# %% ../nbs/cancer_dataloading.ipynb 22
actinickeratosis_names_valid=['ISIC_0030491.jpg','ISIC_0030586.jpg','ISIC_0030655.jpg','ISIC_0030730.jpg','ISIC_0030825.jpg','ISIC_0030826.jpg','ISIC_0030877.jpg','ISIC_0031040.jpg','ISIC_0031108.jpg','ISIC_0031228.jpg','ISIC_0031292.jpg','ISIC_0031335.jpg','ISIC_0031381.jpg','ISIC_0031430.jpg','ISIC_0031506.jpg','ISIC_0031609.jpg','ISIC_0031823.jpg','ISIC_0031922.jpg','ISIC_0031993.jpg','ISIC_0032135.jpg']

# %% ../nbs/cancer_dataloading.ipynb 26
def get_resnet_encoder(model,n_in=3):
    model = create_body(model, n_in=n_in, pretrained=False, cut=len(list(model.children()))-1)
    model.add_module('flatten', torch.nn.Flatten())
    return model


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

# %% ../nbs/cancer_dataloading.ipynb 28
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


