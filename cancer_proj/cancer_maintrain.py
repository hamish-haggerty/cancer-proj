# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/cancer_maintrain.ipynb.

# %% auto 0
__all__ = ['LM', 'my_splitter', 'my_splitter_bt', 'LinearBt', 'fine_tune', 'get_dls_metrics', 'get_xval_metrics', 'Mean_Results',
           'main_tune', 'predict_whole_model']

# %% ../nbs/cancer_maintrain.ipynb 4
from fastai.vision.all import *
from base_rbt.all import *
from .cancer_dataloading import *
from .cancer_metrics import *

# %% ../nbs/cancer_maintrain.ipynb 5
@patch
def lf(self:BarlowTwins, pred,*yb): return lf_bt(pred,I=self.I,lmb=self.lmb)

# %% ../nbs/cancer_maintrain.ipynb 7
class LM(nn.Module):
    "Basic linear model"
    def __init__(self,encoder,numout,numin=2048):
        super().__init__()
        self.encoder=encoder
        self.head=nn.Linear(numin,numout)
        if torch.cuda.is_available():
            self.encoder.cuda()
            self.head.cuda()

    def forward(self,x):
        return self.head(self.encoder(x))

# %% ../nbs/cancer_maintrain.ipynb 8
def my_splitter(m):
    return L(sequential(*m.encoder),m.head).map(params)

def my_splitter_bt(m):
    return L(sequential(*m.encoder),m.projector).map(params)


# %% ../nbs/cancer_maintrain.ipynb 18
class LinearBt(Callback):
    order,run_valid = 9,True
    def __init__(self,aug_pipelines,n_in, show_batch=False, print_augs=False,data=None,
                 tune_model_path=None,tune_save_after=None):
        self.aug1= aug_pipelines[0]
        self.aug2=Pipeline( split_idx = 0) #empty pipeline
        if print_augs: print(self.aug1), print(self.aug2)
        self.n_in=n_in
        self._show_batch=show_batch
        self.criterion = nn.CrossEntropyLoss()
        self.data=data #if data is just e.g. 20 samples then don't bother re-loading each time
        self.tune_model_path=tune_model_path
        self.tune_save_after = tune_save_after


    def after_create(self):
        self.learn.tune_model_path_dict = {}
        self.learn.tune_model_path=self.tune_model_path


    def before_fit(self):
        self.learn.loss_func = self.lf
            
    def before_batch(self):

        if self.n_in == 1:
            xi,xj = self.aug1(TensorImageBW(self.x)), self.aug2(TensorImageBW(self.x))                            
        elif self.n_in == 3:
            xi,xj = self.aug1(TensorImage(self.x)), self.aug2(TensorImage(self.x))
        self.learn.xb = (xi,)

        if self._show_batch:
            self.learn.aug_x = torch.cat([xi, xj])

            
    def after_epoch(self):
        
        true_epoch = self.epoch+1
        
        if true_epoch%self.tune_save_after == 0 and self.learn.tune_model_path!=None:
            #self.learn.tune_path = self.learn.tune_path +f'_epochs={self.n_epoch//50}'
            #path = self.learn.tune_model_path + f'_epochs={true_epoch}'
            
            path = self.learn.tune_model_path
            print(f'We are saving after true epoch {true_epoch} at path {path}')
            torch.save(self.learn.model.state_dict(), path)
            #self.learn.tune_model_path_dict[true_epoch]=path


    def lf(self, pred, *yb):        
        loss=self.criterion(pred,self.y)
        return loss

    @torch.no_grad()
    def show(self, n=1):
        if self._show_batch==False:
            print('Need to set show_batch=True')
            return
        bs = self.learn.aug_x.size(0)//2
        x1,x2  = self.learn.aug_x[:bs], self.learn.aug_x[bs:]
        idxs = np.random.choice(range(bs),n,False)
        x1 = self.aug1.decode(x1[idxs].to('cpu').clone(),full=False).clamp(0,1) #full=True / False
        x2 = self.aug2.decode(x2[idxs].to('cpu').clone(),full=False).clamp(0,1) #full=True / False
        images = []
        for i in range(n): images += [x1[i],x2[i]]
        return show_batch(x1[0], None, images, max_n=len(images), nrows=n)

# %% ../nbs/cancer_maintrain.ipynb 19
def fine_tune(initial_weights,dls_tune,device,aug_pipelines_tune,encoder=None,epochs=40,tune_model_path=None):
    
    
    if encoder is None: #Generally speaking, this will be None, unless we pretrained an encoder somewhere else and want to pass it in
        _,encoder = create_model(initial_weights,device) #either bt_pretrain, supervised_pretrain etc
    

    print(f'tune_model_path for this run is: {tune_model_path}')
    model = LM(encoder,numout=len(dls_tune.vocab))
    learn = Learner(dls_tune,model,splitter=my_splitter,
                        cbs = [LinearBt(aug_pipelines=aug_pipelines_tune,
                                        n_in=3,tune_model_path=tune_model_path, #if None then don't save
                                    tune_save_after=epochs)],wd=0.0
                        
                   )
    
    if initial_weights!='no_pretrain': #Means we are in transfer learning setting
        learn.freeze()
        print('Froze head')
        learn.fit(1)
        learn.unfreeze()
        print('Unfroze head')
    
    lrs = learn.lr_find()
    lr_max=lrs.valley
    print(f'Learning rate finder yielded lr_max: {lr_max}')
    learn.fit_one_cycle(epochs,lr_max)

    return model


def get_dls_metrics(dls,model,aug_pipelines_test,int_to_classes): #note that we can't call dls.vocab as it might be smaller on the test set
    "get metrics from model and dataloader"

    ytest,probs,preds,Acc = predict_whole_model(dls,model,aug_pipelines_test,numavg=3)
    metrics = classification_report_wrapper(preds, ytest,int_to_classes, print_report=True)
    
    plot_roc(ytest,probs,int_to_classes)
    auc_dict = Auc_Dict(ytest,probs,int_to_classes)
    print(f'auc_dict is: {auc_dict}')
    plot_pr(ytest,probs,int_to_classes)
    pr_dict = Pr_Dict(ytest,probs,int_to_classes)
    print(f'auc_dict is: {pr_dict}')

    metrics['ytest']=ytest
    metrics['probs']=probs
    metrics['preds']=preds
    metrics['acc']=Acc
    metrics['auc_dict']=auc_dict
    metrics['pr_dict']=pr_dict

    return metrics

def get_xval_metrics(xval,yval,model,aug_pipelines_test,int_to_classes,numavg=3): #note that we can't call dls.vocab as it might be smaller on the test set
    "get metrics from gives batch (xval,yval)"

    probs,preds,Acc = predict_model(xval,yval,model,aug_pipelines_test,numavg=3)
    metrics = classification_report_wrapper(preds, yval,int_to_classes, print_report=True)
    metrics['acc']=Acc

    return metrics

def Mean_Results(results):
    "Get mean classif report and display it"

    lst = list(vocab) + ['accuracy', 'macro avg', 'weighted avg']
    reports=[]
    accs=[]
    for i in results.keys():
        if type(i)!=int:
            continue
        report = {j:results[i][j] for j in results[i].keys() if j in lst}
        reports.append(report)
        accs.append(results[i]['acc'])
    mean_report = Mean_Report(reports,vocab)
    print(format_classification_report(mean_report))
    
    print(f'mean acc is {mean(accs)} with std {stdev(accs)}')

    return mean_report

#fine tune, return the model and path

def main_tune(initial_weights,dls_tune,dls_test,aug_pipelines_tune,aug_pipelines_test,
              epochs=40,device='cuda',
              encoder=None,tune_model_path=None,dict_path=None,description=None,
              results=None,runs=range(1)
             ):

    "Fine tune and save  test results for supervised or bt initial weights"

    if description == None:
        description=f'Fine tuned {weights} initial weights for 40 epochs. Recorded results on test sets. Did this {runs} times'

    if dict_path==None:
        dict_path=f'{weights}_results'

    weights = initial_weights.split('_')[0]

    print(f'Description: {description}\n')
    print(f'The general tune model path is: {tune_model_path} (if None mean no saving)')
    print(f'The dict_path is: {dict_path}')
    
    if results==None:
        results={}
    
    for i in runs:

        _tune_model_path = None if tune_model_path is None else tune_model_path + f'_run{i}'

        fine_tuned = fine_tune(initial_weights,dls_tune,device,aug_pipelines_tune,encoder=encoder,epochs=epochs,tune_model_path=_tune_model_path)

        #get the metrics
        metrics = get_dls_metrics(dls_test,fine_tuned,aug_pipelines_test,int_to_classes)
        print(metrics['acc'])
        #put the path in in the metrics and a short description
        metrics['tune_model_path'],metrics['description'] = tune_model_path,description

        results[i] = metrics

    #save
    if tune_model_path!=None:
        print(f'We are saving the dictionary at {dict_path}') #this is a bug. We saved at f'{weights}_results'
        save_dict_to_gdrive(results,save_directory,dict_path)

    return results

# %% ../nbs/cancer_maintrain.ipynb 20
@torch.no_grad()
def predict_whole_model(dls_test, model, aug_pipelines_test, numavg=3, criterion=CrossEntropyLossFlat(), deterministic=False):
    """
    Predicts the labels and probabilities for the entire test set using the specified model and data augmentation
    pipelines. Returns a dictionary containing the labels, probabilities, predicted labels, and accuracy.

    Args:
        dls_test: The test dataloader.
        model: The trained model.
        aug_pipelines_test: The test data augmentation pipelines.
        numavg: The number of times to perform test-time augmentation.
        criterion: The loss function to use for computing the accuracy.
        deterministic: Whether to use deterministic computation.

    Returns:
        A dictionary containing the labels, probabilities, predicted labels, and accuracy.
    """
    model.eval()
    total_len = len(dls_test.dataset)
    y = torch.zeros(total_len, dtype=torch.long)
    probs = torch.zeros(total_len, model.head.out_features)
    ypred = torch.zeros(total_len, dtype=torch.long)

    start_idx = 0
    for xval, yval in dls_test.train:
        end_idx = start_idx + len(xval)
        _probs, _ypred, acc = predict_model(xval, yval, model, aug_pipelines_test, numavg, criterion, deterministic)
        y[start_idx:end_idx] = yval
        probs[start_idx:end_idx] = _probs
        ypred[start_idx:end_idx] = _ypred
        start_idx = end_idx

    # Calculate the overall accuracy
    acc = (ypred == y).float().mean().item()

    # Return the predictions and labels in a dictionary
    #return {'y': y, 'probs': probs, 'ypred': ypred, 'acc': acc}
    return y,probs,ypred,acc

