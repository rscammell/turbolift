# turbolift
Turbolift (originally named ALICE), is an extensible mobile computing platform with built-in speech recognition and media features, written between 2001 and 2005 by Rupert Scammell.

**The code in this repository reflects the state of the code and documentation base at the time of Turbolift's final 2.0 release in 2005. Turbolift has been untouched and unmaintained since this time, and is presented on GitHub largely for the sake of historical interest.**

The application was written in Python 2.1 with external dependencies including [CMU Sphinx II](https://cmusphinx.github.io/) and [Festival Speech Synthesis](https://www.cstr.ed.ac.uk/projects/festival/). Hardware support for a [CrystalFontz CFA-634 serial character LCD](https://www.crystalfontz.com/product/cfa634tfhks-character-module-20x4-rs232-lcd) is provided out-of-the-box.

Turbolift is being re-released with its original licensing, described in [the README and Getting Started Guide](https://github.com/rscammell/turbolift/blob/main/Docs/README), which consists of the GNU General Public License with the exception of [Modules/pyCFontz.py](https://github.com/rscammell/turbolift/blob/main/Modules/pyCFontz.py), which is distributed under the GNU Lesser General Public License.

A basic view of Turbolift's modular, socket-based architecture is shown below. Further documentation including detailed architecture and development guides are located in [Docs](https://github.com/rscammell/turbolift/tree/main/Docs).

![A basic architecture diagram of Turbolift](https://github.com/rscammell/turbolift/blob/main/Docs/turbolift_sc.jpg)


