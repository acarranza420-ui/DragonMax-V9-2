#!/usr/bin/env python3
"""DragonMax 4.9 media-hub expansion: Sports, Anime, Music, Podcasts."""
import repo_release_v48 as _v48
import repo_release as _base

_VERSION = '4.9.0'
_base._RELEASE_VERSION = _VERSION
_base._r.VERSION = _VERSION
_base._r.REPO = _base._r.REPO.replace('4.8.0', _VERSION).replace('4.7.0', _VERSION)
_base._r.ADDON = _base._r.ADDON.replace('4.8.0', _VERSION).replace('4.7.0', _VERSION)
_base._r.DEFAULT = _base._r.DEFAULT.replace('4.8.0', _VERSION).replace('4.7.0', _VERSION)

# Nine top-level entries keeps Fire TV remote navigation predictable. Realm and
# specialist destinations remain fully available through Dragon Portal.
_base._DRAGONMAX_MAINMENU = '''<?xml version="1.0" encoding="UTF-8"?>
<shortcuts>
 <shortcut><label>Dragon Portal</label><label2>DragonMax</label2><defaultID>dragonportal</defaultID><icon>special://home/artwork/realm_crests/dragon_order_crest.png</icon><thumb>special://home/artwork/portal_graphics/dragon_order_portal.png</thumb><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=portal)</action></shortcut>
 <shortcut><label>Continue Watching</label><label2>DragonMax</label2><defaultID>continuewatching</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=continue)</action></shortcut>
 <shortcut><label>Movies</label><label2>DragonMax</label2><defaultID>movies</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=movies)</action></shortcut>
 <shortcut><label>TV Shows</label><label2>DragonMax</label2><defaultID>tvshows</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=tv)</action></shortcut>
 <shortcut><label>Sports</label><label2>DragonMax Media</label2><defaultID>sports</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=sports)</action></shortcut>
 <shortcut><label>Anime</label><label2>DragonMax Media</label2><defaultID>anime</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=anime)</action></shortcut>
 <shortcut><label>Music</label><label2>DragonMax Media</label2><defaultID>music</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=music)</action></shortcut>
 <shortcut><label>Podcasts</label><label2>DragonMax Media</label2><defaultID>podcasts</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=podcasts)</action></shortcut>
 <shortcut><label>Settings</label><label2>DragonMax</label2><defaultID>settings</defaultID><action>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=settings)</action></shortcut>
</shortcuts>'''

home = _base._DRAGONMAX_HOME_XML
# Anime becomes a content destination rather than only a realm switch.
home = home.replace('RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=arcane_dominion)', 'RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=anime)', 1)
# Main nav moves down into a dedicated media row instead of jumping straight to posters.
home = home.replace('<ondown>6100</ondown>', '<ondown>5010</ondown>')
media_row = '''
  <control type="group"><left>70</left><top>710</top><animation effect="fade" start="0" end="100" time="420" delay="410">WindowOpen</animation><animation effect="slide" start="0,18" end="0,0" time="420" delay="410">WindowOpen</animation>
   <control type="button" id="5010"><left>0</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>SPORTS</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=sports)</onclick><onleft>5013</onleft><onright>5011</onright><onup>5001</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
   <control type="button" id="5011"><left>225</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>ANIME</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=anime)</onclick><onleft>5010</onleft><onright>5012</onright><onup>5005</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
   <control type="button" id="5012"><left>450</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>MUSIC</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=music)</onclick><onleft>5011</onleft><onright>5013</onright><onup>5004</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
   <control type="button" id="5013"><left>675</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>PODCASTS</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=podcasts)</onclick><onleft>5012</onleft><onright>5010</onright><onup>5009</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
  </control>
'''
home = home.replace('  <control type="label"><left>70</left><top>735</top>', media_row + '\n  <control type="label"><left>70</left><top>790</top>', 1)
home = home.replace('<control type="fixedlist" id="6100"><left>70</left><top>785</top><width>1780</width><height>245</height>', '<control type="fixedlist" id="6100"><left>70</left><top>835</top><width>1780</width><height>205</height>', 1)
home = home.replace('<onup>5001</onup>', '<onup>5010</onup>', 1)
_base._DRAGONMAX_HOME_XML = home

from repo_release_v48 import *
DEFAULT = _base._r.DEFAULT
