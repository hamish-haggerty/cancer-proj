# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/cancer_metrics.ipynb.

# %% auto 0
__all__ = ['predict_model', 'classification_report_wrapper', 'print_confusion_matrix', 'plot_roc']

# %% ../nbs/cancer_metrics.ipynb 6
#Fine tune and predict

@torch.no_grad()
def predict_model(xval,yval,model,aug_pipelines_test,numavg=3):
    "Note that this assumes xval is entire validation set. If it doesn't fit in memory, can't use this guy"
    
    model.eval()

    test_eq(model.encoder.training,False)

    N=xval.shape[0]

    scores=0
    for _ in range(numavg):

        scores += model(aug_pipelines_test(xval)) #test time augmentation. This also gets around issue of randomness in the dataloader in each session...

    scores *= 1/numavg

    ypred = cast(torch.argmax(scores, dim=1),TensorCategory)

    correct = (ypred == yval)#.type(torch.FloatTensor)

    #correct = (torch.argmax(ypred,dim=1) == yval).type(torch.FloatTensor)
    num_correct = correct.sum()
    accuracy = num_correct/N
    
    return scores,ypred,accuracy.item()



# %% ../nbs/cancer_metrics.ipynb 7
from sklearn.metrics import classification_report

def classification_report_wrapper(ypred, y, vocab, print_report=True):
    # Convert ypred and y to numpy arrays
    ypred = ypred.cpu().numpy()
    y = y.cpu().numpy()
    
    # Get the class labels from vocab
    labels = [vocab[i] for i in range(len(vocab))]
    
    # Get the classification report as a dictionary
    report = classification_report(y, ypred, target_names=labels, output_dict=True)
    
    if print_report:
        print(classification_report(y, ypred, target_names=labels))
        
    return report


# %% ../nbs/cancer_metrics.ipynb 8
import seaborn as sns
import pandas as pd
from sklearn.metrics import confusion_matrix

def print_confusion_matrix(ypred, y, vocab):
    # Convert ypred and y to numpy arrays
    ypred = ypred.cpu().numpy()
    y = y.cpu().numpy()
    
    # Get the class labels from vocab
    labels = [vocab[i] for i in range(len(vocab))]
    
    # Create the confusion matrix
    cm = confusion_matrix(y, ypred)
    
    # Create a DataFrame from the confusion matrix
    df_cm = pd.DataFrame(cm, index = labels, columns = labels)
    
    # Use seaborn to create a heatmap of the confusion matrix with blue and white colors
    sns.heatmap(df_cm, annot=True, cmap="Blues")


# %% ../nbs/cancer_metrics.ipynb 9
from sklearn.metrics import roc_curve, auc
from sklearn.preprocessing import label_binarize
import matplotlib.pyplot as plt

def plot_roc(yval,ypred,vocab,print_plot=True):
    "plot 1 vs all roc curves"

    yval = yval.cpu().numpy()
    ypred = ypred.cpu().numpy()

    N=len(vocab)
    # Binarize the output
    y_true = label_binarize(yval, classes=list(range(N)))
    y_pred = label_binarize(ypred, classes=list(range(N)))

    # Compute ROC for each class
    fpr = dict()
    tpr = dict()
    roc_auc = dict()
    for i in range(N):
        fpr[i], tpr[i], _ = roc_curve(y_true[:, i], y_pred[:, i])
        roc_auc[i] = auc(fpr[i], tpr[i])

    auc_dict = dict(zip([vocab[i] for i in roc_auc.keys()],list(roc_auc.values()))) #just change keys from e.g. 0 to 'actinic keratosis'

    if print_plot == False: return auc_dict

    # Plot ROC for each class
    plt.figure(figsize=(7,5))
    lw = 2
    for i in range(N):
        plt.plot(fpr[i], tpr[i], lw=lw, label='{0} (area = {1:0.2f})'.format(vocab[i], roc_auc[i]))
    plt.plot([0, 1], [0, 1], 'k--', lw=lw)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Multi-class ROC')
    #plt.legend(loc="lower right")
    plt.legend(loc="lower right", fontsize=8)
    

    return auc_dict

#auc_dict = plot_roc(yval=yval,ypred=preds,vocab=vocab,print_plot=False)