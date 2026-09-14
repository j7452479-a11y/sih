- Skip to main contentCtrl + K
- Go to   pytorch.org Ctrl + K  X
- GitHub
- PyTorch Forum
- PyPi
- Go to   pytorch.org Ctrl + K  X
- GitHub
- PyTorch Forum
- PyPi
Rate this Page  ★   ★   ★   ★   ★
# torch.bucketize[#](https://pytorch.org#torch-bucketize)
torch. bucketize (input, boundaries, \*, out\_int32 = False, right = False, out = None)   →  [Tensor](https://pytorch.org/tensors.html#torch.Tensor)[#](https://pytorch.org/tensors.html#torch.Tensor)Returns the indices of the buckets to which each value in the  input  belongs, where the boundaries of the buckets are set by  boundaries . Return a new tensor with the same size as  input . If  right  is False (default), then the left boundary is open. Note that this behavior is opposite the behavior of [numpy.digitize](https://numpy.org/doc/stable/reference/generated/numpy.digitize.html). More formally, the returned index satisfies the following rules:
right
returned index satisfies
False
boundaries\[i-1\]   <   input\[m\]\[n\]...\[l\]\[x\]   <=   boundaries\[i\]
True
boundaries\[i-1\]   <=   input\[m\]\[n\]...\[l\]\[x\]   <   boundaries\[i\]
Parameters :
***input*** (Tensor or Scalar) – N-D tensor or a Scalar containing the search value(s).
***boundaries*** (Tensor) – 1-D tensor, must contain a strictly increasing sequence, or the return value is undefined.
Keyword Arguments :
***out\_int32*** (bool, optional) – indicate the output data type. torch.int32 if True, torch.int64 otherwise. Default value is False, i.e. default output data type is torch.int64.
***right*** (bool, optional) – determines the behavior for values in  boundaries . See the table above.
***out*** (Tensor, optional) – the output tensor, must be the same size as  input  if provided.
Example:
>>>  boundaries   =   torch . tensor (\[ 1 ,   3 ,   5 ,   7 ,   9 \])   >>>  boundaries   tensor(\[1, 3, 5, 7, 9\])   >>>  v   =   torch . tensor (\[\[ 3 ,   6 ,   9 \],   \[ 3 ,   6 ,   9 \]\])   >>>  v   tensor(\[\[3, 6, 9\],    \[3, 6, 9\]\])   >>>  torch . bucketize ( v ,   boundaries )   tensor(\[\[1, 3, 4\],    \[1, 3, 4\]\])   >>>  torch . bucketize ( v ,   boundaries ,   right = True )   tensor(\[\[2, 3, 5\],    \[2, 3, 5\]\])  previous
torch.broadcast\_shapes
next
torch.cartesian\_prod
Built with the [PyData Sphinx Theme](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html) 0.15.4.
- [ On this page ](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
[ Show Source ](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)PyTorch Libraries
- [ExecuTorch](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [Helion](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [torchao](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [kineto](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [torchtitan](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [TorchRL](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [torchvision](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [torchaudio](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [tensordict](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
- [PyTorch on XLA Devices](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
## Docs
Access comprehensive developer documentation for PyTorch
## [View Docs](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)Tutorials
Get in-depth tutorials for beginners and advanced developers
## [View Tutorials](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)Resources
Find development resources and get your questions answered
[View Resources](https://pydata-sphinx-theme.readthedocs.io/en/stable/index.html)
To analyze traffic and optimize your experience, we serve cookies on this site. By clicking or navigating, you agree to allow our usage of cookies. As the current maintainers of this site, Facebook’s Cookies Policy applies. Learn more, including about available controls: [Cookies Policy](https://opensource.fb.com/legal/cookie-policy).