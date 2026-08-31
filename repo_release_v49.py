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


def portal_window(target):
    """Open the Portal plugin in a real Programs window so directory actions render."""
    return 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/?action=open&amp;target=' + target + '",return)'


# Nine top-level entries keeps Fire TV remote navigation predictable. Every
# destination is opened as a Kodi window, rather than RunPlugin(), because the
# Portal is a directory-style plugin and Fire TV must actually display the result.
_base._DRAGONMAX_MAINMENU = '''<?xml version="1.0" encoding="UTF-8"?>
<shortcuts>
 <shortcut><label>Dragon Portal</label><label2>DragonMax</label2><defaultID>dragonportal</defaultID><icon>special://home/artwork/realm_crests/dragon_order_crest.png</icon><thumb>special://home/artwork/portal_graphics/dragon_order_portal.jpg</thumb><action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action></shortcut>
 <shortcut><label>Continue Watching</label><label2>DragonMax</label2><defaultID>continuewatching</defaultID><action>''' + portal_window('continue') + '''</action></shortcut>
 <shortcut><label>Movies</label><label2>DragonMax</label2><defaultID>movies</defaultID><action>''' + portal_window('movies') + '''</action></shortcut>
 <shortcut><label>TV Shows</label><label2>DragonMax</label2><defaultID>tvshows</defaultID><action>''' + portal_window('tv') + '''</action></shortcut>
 <shortcut><label>Sports</label><label2>DragonMax Media</label2><defaultID>sports</defaultID><action>''' + portal_window('sports') + '''</action></shortcut>
 <shortcut><label>Anime</label><label2>DragonMax Media</label2><defaultID>anime</defaultID><action>''' + portal_window('anime') + '''</action></shortcut>
 <shortcut><label>Music</label><label2>DragonMax Media</label2><defaultID>music</defaultID><action>''' + portal_window('music') + '''</action></shortcut>
 <shortcut><label>Podcasts</label><label2>DragonMax Media</label2><defaultID>podcasts</defaultID><action>''' + portal_window('podcasts') + '''</action></shortcut>
 <shortcut><label>Settings</label><label2>DragonMax</label2><defaultID>settings</defaultID><action>''' + portal_window('settings') + '''</action></shortcut>
</shortcuts>'''

home = _base._DRAGONMAX_HOME_XML

# Convert every DragonMax Home plugin action into a real window-opening route.
# This includes the inherited 5001-5009 navigation controls from the 4.8 shell.
for target in ('portal','continue','movies','tv','sports','anime','music','podcasts','settings'):
    old = 'RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=' + target + ')'
    new = portal_window(target) if target != 'portal' else 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)'
    home = home.replace(old, new)

# Anime becomes a content destination rather than only a realm switch.
home = home.replace(
    'RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=arcane_dominion)',
    portal_window('anime'), 1)

# Main nav moves down into a dedicated media row instead of jumping straight to posters.
home = home.replace('<ondown>6100</ondown>', '<ondown>5010</ondown>')
media_row = '''
  <control type="group"><left>70</left><top>710</top><animation effect="fade" start="0" end="100" time="420" delay="410">WindowOpen</animation><animation effect="slide" start="0,18" end="0,0" time="420" delay="410">WindowOpen</animation>
   <control type="button" id="5010"><left>0</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>SPORTS</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>''' + portal_window('sports') + '''</onclick><onleft>5013</onleft><onright>5011</onright><onup>5001</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
   <control type="button" id="5011"><left>225</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>ANIME</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>''' + portal_window('anime') + '''</onclick><onleft>5010</onleft><onright>5012</onright><onup>5005</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
   <control type="button" id="5012"><left>450</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>MUSIC</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>''' + portal_window('music') + '''</onclick><onleft>5011</onleft><onright>5013</onright><onup>5004</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
   <control type="button" id="5013"><left>675</left><top>0</top><width>210</width><height>58</height><font>font20</font><label>PODCASTS</label><texturefocus colordiffuse="FFFFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="44222222">common/white.png</texturenofocus><textcolor>FFFFFFFF</textcolor><focusedcolor>FF111111</focusedcolor><onclick>''' + portal_window('podcasts') + '''</onclick><onleft>5012</onleft><onright>5010</onright><onup>5009</onup><ondown>6100</ondown><animation effect="zoom" start="100" end="110" time="120" center="auto" reversible="true">Focus</animation></control>
  </control>
'''
home = home.replace('  <control type="label"><left>70</left><top>735</top>', media_row + '\n  <control type="label"><left>70</left><top>790</top>', 1)
home = home.replace('<control type="fixedlist" id="6100"><left>70</left><top>785</top><width>1780</width><height>245</height>', '<control type="fixedlist" id="6100"><left>70</left><top>835</top><width>1780</width><height>205</height>', 1)
home = home.replace('<onup>5001</onup>', '<onup>5010</onup>', 1)

# Real recovered Portal art is JPEG. Do not point the UI at the old generated PNG.
home = home.replace('special://home/artwork/portal_graphics/dragon_order_portal.png', 'special://home/artwork/portal_graphics/dragon_order_portal.jpg')
_base._DRAGONMAX_HOME_XML = home

from repo_release_v48 import *
DEFAULT = _base._r.DEFAULT
