import hashlib # retorna um valor opaco de ETag.
import os
import sys

from django.conf import settings

DEBUG = os.environ.get('DEBUG', 'on') == 'on'
SECRET_KEY = os.environ.get('SECRET_KEY', '9+n(1i@3voejxdb1*y0#hp)nxju#zzr4nk5u-6v=r#utomfzpl')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')

settings.configure(
    DEBUG=DEBUG,
    SECRET_KEY=SECRET_KEY,
    ALLOWED_HOSTS=ALLOWED_HOSTS,
    ROOT_URLCONF=__name__,
    MIDDLEWARE_CLASSES=(
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ),
)

from io import BytesIO
from PIL import Image, ImageDraw
from django import forms
from django.conf.urls import url
from django.core.cache import cache # verifica se a imagem já está armazenada.
from django.core.wsgi import get_wsgi_application
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import etag

class ImageForm(forms.Form):
    """Formulário para validar o placeholder de imagem solicitado."""

    height = forms.IntegerField(min_value=1, max_value=2000)
    width = forms.IntegerField(min_value=1, max_value=2000)

    def generate(self, image_format='PNG'):
        """Gera uma imagem do tipo especificado e a retorna na forma de bytes puros."""
        height = self.cleaned_data['height']
        width = self.cleaned_data['width']
        # uma chave de cache dependente da largura, da altura e do formato da imagem é gerada:
        key = '{}.{}.{}'.format(width, height, image_format)
        # verifica se a imagem já está armazenada:
        content = cache.get(key)
        if content is None:
            image = Image.new('RGB', (width, height))
            draw = ImageDraw.Draw(image)
            text = '{} X {}'.format(width, height)
            textwidth, textheight = draw.textsize(text)
            if textwidth < width and textheight < height:
                texttop = (height - texttheight) // 2
                textleft = (width - textwidth) // 2
                draw.text((textleft, texttop), text, fill=(255, 255, 255))
            content = BytesIO()
            image.save(content, image_format)
            content.seek(0)
            # quando a imagem não estiver no cache e for criada, ela será armazenada no cache com a chave durante uma hora:
            cache.set(key, content, 60 * 60)
        return content

# generate_etag é uma função que recebe os mesmos argumentos que a viewplaceholder. Ela usa hashlib para retornar um valor opaco de ETag, que variará de acordo com os valores de width e de height:
def generate_etag(request, width, height):
    content = 'Placeholder: {0} X {1}'.format(width, height)
    return hashlib.sha1(content.encode('utf-8')).hexdigest()

# a função generate_etag será passada ao decorador etag na view placeholder:
@etag(generate_etag)
def placeholder(request, width, height):
    form = ImageForm({'height': height, 'width': width})
    if form.is_valid():
        image = form.generate()
        return HttpResponse(image, content_type='image/png')
    else:
        return HttpResponseBadRequest('Invalid Image Request')

def index(request):
    return HttpResponse('Hello Word')

urlpatterns = [
    url(r'^image/(?P<width>[0-9]+)x(?P<height>[0-9]+)/?', placeholder,
        name='placeholder'),
    url(r'^$', index, name='homepage'),
]

application = get_wsgi_application()

if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
