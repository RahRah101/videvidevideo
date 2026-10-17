# Order matters: resolve_media takes the first handler that matches.
# ytdlp claims every URL, so it goes last.
from . import image_url
from . import ytdlp
