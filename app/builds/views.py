import os, shutil

from django.shortcuts import render, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import FileSystemStorage

from common_modules import fedClass
from common_modules.security import access_granted, is_admin
from common_modules.amsettings import APPLICATIONS, get_access_config

import urllib2
from os import listdir
from os.path import isfile, join, dirname
import zipfile, re
from am_tools import settings
from .utils import handle_uploaded_file

# Create your views here.

@login_required
def index(request):

    file_path = settings.MEDIA_ROOT
    dirs = [f for f in listdir(file_path) if not isfile(join(file_path, f))]
    if len(dirs) > 0:
        dirs = sorted(dirs, reverse=True)
        latest = max(dirs) if len(dirs) > 1 else ''
    else:
        dirs = []
        latest = ''

    return render(request, 'builds/index.html', {'versions': dirs, 'latest': latest})

@login_required
def build(request, version):

    if version == 'latest':
        file_path = settings.MEDIA_ROOT
        dirs = [f for f in listdir(file_path) if not isfile(join(file_path, f))]
        if len(dirs) > 0:
            dirs = sorted(dirs, reverse=True)
            version = max(dirs) if len(dirs) > 1 else ''

    full_version = settings.MEDIA_URL + version
    with open(join(settings.MEDIA_ROOT, version, 'index.html'), 'rb+') as f:
        index = str.join('', f.readlines())
    try:
        loaderUrl = re.search('buildUrl \+ "\/(.+?)";', index).group(1)
        dataUrl = re.search('dataUrl: buildUrl \+ "\/(.+?)",', index).group(1)
        frameworkUrl = re.search('frameworkUrl: buildUrl \+ "\/(.+?)",', index).group(1)
        codeUrl = re.search('codeUrl: buildUrl \+ "\/(.+?)",', index).group(1)
        streamingAssetsUrl = re.search('streamingAssetsUrl: "(.+?)",', index).group(1)
        companyName = re.search('companyName: "(.+?)",', index).group(1)
        productName = re.search('productName: "(.+?)",', index).group(1)
        productVersion = re.search('productVersion: "(.+?)",', index).group(1)
        showBanner = re.search('showBanner: (.+?),', index).group(1)
    except AttributeError:
        return render('Error')

    return render(request, 'builds/build.html', {'version': full_version,
                                                 'loaderUrl': loaderUrl,
                                                 'dataUrl': dataUrl,
                                                 'frameworkUrl': frameworkUrl,
                                                 'codeUrl': codeUrl,
                                                 'streamingAssetsUrl': streamingAssetsUrl,
                                                 'companyName': companyName,
                                                 'productName': productName,
                                                 'productVersion': productVersion,
                                                 'showBanner': showBanner})

@login_required
def simple_upload(request):
    if request.method == 'POST' and len(request.FILES) > 0 and request.FILES['file']:
        myfile = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)
        with zipfile.ZipFile(fs.path(filename), 'r') as zip_ref:
            zip_ref.extractall(dirname(fs.path(filename)))
        os.remove(fs.path(filename))
        return render(request, 'builds/upload.html', {
            'uploaded_file_url': uploaded_file_url
        })
    return render(request, 'builds/upload.html')

@login_required
def delete(request, version):

    path = join(settings.MEDIA_ROOT, version)

    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)

    return index(request)
