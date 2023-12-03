import os.path as osp
import ctypes


def load_embedded_hidapi_lib():
    lib_path = osp.join(osp.dirname(__file__), 'hidapi.dll')
    ctypes.cdll.LoadLibrary(lib_path)


load_embedded_hidapi_lib()
