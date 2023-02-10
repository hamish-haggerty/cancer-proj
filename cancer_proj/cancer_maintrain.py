# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/cancer_maintrain.ipynb.

# %% auto 0
__all__ = ['LM', 'my_splitter', 'my_splitter_bt', 'main_train']

# %% ../nbs/cancer_maintrain.ipynb 5
from fastai.vision.all import *
from base_rbt.all import *
from .cancer_dataloading import *
from .cancer_metrics import *

# %% ../nbs/cancer_maintrain.ipynb 13
@patch
def lf(self:BarlowTwins, pred,*yb): return lf_bt(pred,I=self.I,lmb=self.lmb)

# %% ../nbs/cancer_maintrain.ipynb 15
class LM(nn.Module):
    "Basic linear model"
    def __init__(self,encoder):
        super().__init__()
        self.encoder=encoder
        self.head=nn.Linear(2048,9)
        if torch.cuda.is_available():
            self.encoder.cuda()
            self.head.cuda()

    def forward(self,x):
        return self.head(self.encoder(x))

#TODO: write nonlinear head here as well if needed. Just need batchnorm, relu another hidden layer

# %% ../nbs/cancer_maintrain.ipynb 16
def my_splitter(m):
    return L(sequential(*m.encoder),m.head).map(params)

def my_splitter_bt(m):
    return L(sequential(*m.encoder),m.projector).map(params)


# %% ../nbs/cancer_maintrain.ipynb 27
@patch
@delegates(Learner.fit_one_cycle)
def linear_fine_tune(self:Learner, epochs, base_lr=2e-3, freeze_epochs=1, lr_mult=100,
              pct_start=0.3, div=5.0, **kwargs):
    "Extremely minor change to fine_tune, but seems to work better"
    
    self.freeze()
    self.fit_one_cycle(freeze_epochs, slice(base_lr), pct_start=0.99, **kwargs)
    base_lr /= 2
    self.unfreeze()
    #self.fit_one_cycle(epochs, slice(base_lr/lr_mult, base_lr), pct_start=pct_start, div=div, **kwargs)
    self.fit_one_cycle(epochs, slice(base_lr, base_lr), pct_start=pct_start, div=div, **kwargs)

# %% ../nbs/cancer_maintrain.ipynb 29
@patch
@delegates(Learner.fit_one_cycle)
def encoder_fine_tune(self:Learner, epochs, base_lr=2e-3, freeze_epochs=1, lr_mult=100,
              pct_start=0.3, div=5.0, **kwargs):
    "Extremely minor change to fine_tune, but seems to work better"

    
    self.freeze()
    self.fit_one_cycle(freeze_epochs, slice(base_lr), pct_start=0.99, **kwargs)
    base_lr /= 2
    self.unfreeze()
    #self.fit_one_cycle(epochs, slice(base_lr/lr_mult, base_lr), pct_start=pct_start, div=div, **kwargs)
    self.fit_one_cycle(epochs, slice(base_lr, base_lr), pct_start=pct_start, div=div, **kwargs)

# %% ../nbs/cancer_maintrain.ipynb 30
class main_train:
    """Instantiate and (optionally) train the encoder. Then fine-tune the supervised model. 
    Outputs metrics on validation data"""

    def __init__(self,
                 dls_train, #used for training BT (if pretrain=True)
                 dls_tune , #used for tuning
                 dls_valid, #used to compute metrics / evaluate results. 
                 xval, #currently `predict_model` below assumes this is entire validation / test data
                 yval,
                 aug_pipelines, #the aug pipeline for self-supervised learning
                 aug_pipelines_tune, #the aug pipeline for supervised learning
                 aug_pipelines_test, #test (or valid) time augmentations 
                 initial_weights, #Which initial weights to use
                 pretrain, #Whether to fit BT
                 num_epochs, #number of BT fit epochs
                 numfit, #number of tune_fit epochs
                 freeze_num_epochs, #How many epochs to freeze body for when training BT
                 freeze_numfit, #How many epochs to freeze body for when fine tuning
                 ps=8192, #projection size
                 n_in=3, #color channels
                 indim=2048, #dimension output of encoder (2048 for resnet50)
                 outdim=9, #number of classes
                 print_report=False, #F1 metrics etc
                 print_plot=False, #ROC curve
                 ):
        store_attr()
        self.vocab = self.dls_valid.vocab
        self.device = 'cuda' if torch.cuda.is_available else 'cpu'

                
                 

                 #Soon we might want to save some models here:

                 #if self.model_type == 'res_proj': test_eq(self.fit_policy,'resnet_fine_tune') #I THINK this is only viable option?
                 #self.encoder_path = f'/content/drive/My Drive/models/baselineencoder_initial_weights={self.initial_weights}_pretrain={self.pretrain}.pth'
                 #self.tuned_model_path = f'/content/drive/My Drive/models/baselinefinetuned_initial_weights={self.initial_weights}_pretrain={self.pretrain}.pth'

    @staticmethod
    def fit(learn,fit_type,epochs,freeze_epochs,initial_weights):
        """We can patch in a modification, e.g. if we want subtype of fine_tune:supervised_pretrain to be different
        to fine_tune:bt_pretrain"""

        if fit_type == 'encoder_fine_tune': #i.e. barlow twins

            learn.encoder_fine_tune(epochs,freeze_epochs=freeze_epochs) 

        elif fit_type == 'fine_tune':
            
            #elif initial_weights == 'supervised_pretrain':
            learn.linear_fine_tune(epochs,freeze_epochs=freeze_epochs) 

        else: raise Exception('Fit policy not of expected form')

    def train_encoder(self):
        "create encoder and (optionally, if pretrain=True) train with BT algorithm, according to fit_policy"

        try: #get existing encoder and plonk on new projector
            encoder = self.encoder
            encoder.cpu()
            bt_model = create_barlow_twins_model(encoder, hidden_size=self.ps,projection_size=self.ps,nlayers=3)
            bt_model.cuda()

        except AttributeError: #otherwise, create
            bt_model,encoder = create_model(which_model=self.initial_weights,ps=self.ps,device=self.device)

        if self.pretrain: #train encoder according to fit policy

            learn = Learner(self.dls_train,bt_model,splitter=my_splitter_bt,cbs=[BarlowTwins(self.aug_pipelines,n_in=self.n_in,lmb=1/self.ps,print_augs=False)])
            main_train.fit(learn,fit_type='encoder_fine_tune',
                           epochs=self.num_epochs,freeze_epochs=self.freeze_num_epochs,
                           initial_weights=self.initial_weights
                          )
            
        self.encoder = bt_model.encoder

    def fine_tune(self):
        "fine tune in supervised fashion, according to tune_fit_policy, and get metrics"

        #encoder = pickle.loads(pickle.dumps(self.encoder)) #We might want to pretrain once and fine tune several times (varying e.g. tune augs)

        try: 
            encoder = self.encoder
        
        except AttributeError:
            _,self.encoder = create_model(which_model=self.initial_weights,ps=self.ps,device=device)

        model = LM(self.encoder)
        learn = Learner(self.dls_tune,model,splitter=my_splitter,cbs = [LinearBt(aug_pipelines=self.aug_pipelines_tune,n_in=self.n_in)],wd=0.0)

        #debugging
        #learn = Learner(self.dls_tune,model,cbs = [LinearBt(aug_pipelines=self.aug_pipelines_tune,n_in=self.n_in)],wd=0.0)

        main_train.fit(learn,fit_type='fine_tune',
                       epochs=self.numfit,freeze_epochs=self.freeze_numfit,
                       initial_weights=self.initial_weights
                      ) #fine tuning (don't confuse this with fit policy!)
        scores,preds, acc = predict_model(self.xval,self.yval,model=model,aug_pipelines_test=self.aug_pipelines_test,numavg=3)
        #metrics dict will have f1 score, auc etc etc
        metrics = classification_report_wrapper(preds, self.yval, self.vocab, print_report=self.print_report)
        auc_dict = plot_roc(self.yval,preds,self.vocab,print_plot=self.print_plot)
        metrics['acc'],metrics['auc_dict'],metrics['scores'],metrics['preds'],metrics['xval'],metrics['yval'] = acc,auc_dict,scores,preds,self.xval,self.yval
  
        #torch.save(model.state_dict(), self.tuned_model_path)
        return metrics #

    def __call__(self):

        self.train_encoder() #train (or extract) the encoder
        metrics = self.fine_tune()
        
        return metrics

if __name__ == '__main__' and on_colab:

    initial_weights = 'supervised_pretrain'
    pretrain=True
    numfit=1
    num_epochs=1

    main = main_train(dls_train=dls_train,dls_tune=dls_tune,dls_valid=dls_valid, xval=xval, yval=yval,
            aug_pipelines=aug_pipelines, aug_pipelines_tune=aug_pipelines_tune, aug_pipelines_test=aug_pipelines_test, 
            initial_weights=initial_weights,pretrain=pretrain,num_epochs=num_epochs,numfit=numfit,
            print_report=True,
                    )
    
    metrics = main()
    

