<h2>Tile Map Framework</h2>
<b>Description:</b><br>
Serves as a lightweight, modular Python framework template for rendering interactive, zoomable image tile layers using PyQt5. Designed to support robust geospatial visualization, custom overlays, and integration with external datasets such as map features, infrastructure layers or custom data elements.<br>
<br>
<b>Features</b><br>
- [X] Efficient loading of tiled raster imagery (e.g., `.jpg`, `.png`)<br>
- [X] Built with PyQt5 for cross-platform GUI development<br>
- [X] Interactive click-zoom and mouse wheel functionality<br>
- [X] Modular design for application-specific extension<br>
- [X] Optional data overlays and marker support<br>
- [X] Run-time image caching for smoother performance<br>
- [ ] Pre-run batch image downloading (to disk)<br>
- [ ] Categorical marker filtering<br>
<br>
<b>Installation</b><br>

```bash
git clone https://github.com/gedeon93/tile-map-framework.git
cd tile-map-framework
python -m venv venv
source venv/bin/activate     # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
