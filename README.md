# GIP Router QGIS plugin

**Note, only QGIS v3.x is supported.**

A QGIS plugin used to parse and route through the IDF dataset using for austrian official open government street graph.

## Functionalities

### General

Use QGIS to generate input for **routing**, **isochrones** powered by ORS.

It offers either a GUI in the toolbar of QGIS to interactively use the API's from the map canvas.

## Getting Started

### Prerequisites

QGIS versin: min. **v3.0**

Download IDF datasets used by this router from austrian government open-data platform:

> https://www.data.gv.at/katalog/dataset/intermodales-verkehrsreferenzsystem-osterreich-gip-at-beta/resource/0775cf69-7119-43ec-af09-9da1016a4b94 

Sample OGD dataset included [here](https://github.com/flexarts/giprouter-qgis-plugin/blob/master/data/Routingexport_Wien_OGD.txt) ([Licence](https://github.com/flexarts/giprouter-qgis-plugin/blob/master/data/Routingexport_Wien_OGD.licence.txt)).

### Installation

Either from QGIS plugin repository or manually:
  - [Download](https://github.com/flexarts/giprouter-qgis-plugin/archive/master.zip) ZIP file from Github
  - Unzip folder to `giprouter` and copy folder to:
    - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins`
    - Windows: `C:\Users\USER\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins`
    - Mac OS: `Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins`

## License

This project is published under the MIT license, see [LICENSE.md](https://github.com/giprouter-qgis-plugin/blob/master/LICENSE.md) for details.

