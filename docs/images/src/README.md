# Image sources

`social-preview.html` (1280×640, uploaded in the repo's Settings → Social
preview) and `social-preview-banner.html` (1280×320, the README banner, derived
from the card by an override block at the end of its styles) render with
headless Chrome:

```sh
chrome=/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome
"$chrome" --headless=new --hide-scrollbars --window-size=1280,640 --force-device-scale-factor=1 \
  --virtual-time-budget=4000 --screenshot=../social-preview.png "file://$PWD/social-preview.html"
"$chrome" --headless=new --hide-scrollbars --window-size=1280,320 --force-device-scale-factor=2 \
  --virtual-time-budget=4000 --screenshot=../banner.png "file://$PWD/social-preview-banner.html"
```

The social preview renders at 1x because GitHub caps it at 1 MB. The
notification is redrawn from a real run of the Shortcut; the capsule is a plain
drawing rather than Nespresso's product image, and the coffee beans are placed
from a fixed seed, so every render is the same.
