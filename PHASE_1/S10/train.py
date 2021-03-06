import torch
from tqdm import tqdm

train_acc = []
def train(model, train_loader, device, optimizer, criterion):
    model.train()
    pbar = tqdm(train_loader)
    correct = 0
    processed = 0
    for batch_idx, (data, target) in enumerate(pbar):
        # Get samples
        data, target = data.to(device), target.to(device)

        # Set gradients to zero before starting backpropagation
        optimizer.zero_grad()

        # Predict output
        y_pred = model(data)

        # Calculate loss
        loss = criterion(y_pred, target)

        # Perform backpropagation
        loss.backward()
        optimizer.step()

        # Update progress bar
        pred = y_pred.argmax(dim=1, keepdim=False)
        correct += pred.eq(target).sum().item()
        processed += len(data)
        pbar.set_description(desc=f'Loss={loss.item():0.2f} Batch ID={batch_idx} Accuracy={(100 * correct / processed):.2f}')
        pbar.update(1)
    train_acc = 100*correct/processed
    return train_acc, loss
