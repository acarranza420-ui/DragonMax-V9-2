#!/usr/bin/env python3
"""DragonMax 4.9 media-hub expansion: Sports, Anime, Music, Podcasts."""
import release_home as _v48
import release_presentation as _base

_VERSION = '4.9.0'
_base._RELEASE_VERSION = _VERSION
_base._r.VERSION = _VERSION


def portal_window(target):
    """Open the Portal plugin in a real Programs window so directory actions render."""
    return 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/?action=open&amp;target=' + target + '",return)'


_base._DRAGONMAX_MAINMENU = '''<?xml version="1.0" encoding="UTF-8"?>
<shortcuts>
 <shortcut><label>Dragon Portal</label><label2>DragonMax</label2><defaultID>dragonportal</defaultID><thumb>special://home/artwork/reference/dragonmax_v92_home_preview.png</thumb><action>ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)</action></shortcut>
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

for target in ('portal','continue','movies','tv','sports','anime','music','podcasts','settings'):
    old = 'RunPlugin(plugin://plugin.program.dragonmaxportal/?action=open&amp;target=' + target + ')'
    new = portal_window(target) if target != 'portal' else 'ActivateWindow(Programs,"plugin://plugin.program.dragonmaxportal/",return)'
    home = home.replace(old, new)

home = home.replace(
    'RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=arcane_dominion)',
    portal_window('anime'), 1)

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
home = home.replace('<focusposition>0</focusposition><onup>5001</onup>', '<focusposition>0</focusposition><onup>5010</onup>', 1)

# Bind the presentation layer directly to the recovered V12 art. No generated
# hero or portal placeholder is a valid 4.9 primary asset.
home = home.replace('special://home/artwork/hero_banners/dragon_order/dragon_order_hero_01.png', 'special://home/artwork/reference/dragonmax_v92_home_preview.png')
home = home.replace('special://home/artwork/hero_banners/dragon_order/dragon_order_hero_01.jpg', 'special://home/artwork/reference/dragonmax_v92_home_preview.png')
home = home.replace('special://home/artwork/hero_banners/dragon_order/', 'special://home/artwork/reference/')
home = home.replace('special://home/artwork/portal_graphics/dragon_order_portal.png', 'special://home/artwork/reference/dragonmax_v92_home_preview.png')
home = home.replace('special://home/artwork/realm_crests/dragon_order_crest.png', 'special://home/artwork/reference/dragonmax_v92_home_preview.png')

# The Dragon Order Home screen is the recovered DragonMax dashboard itself, not
# a generic AuraMOD composition with placeholder art around it.  The opaque
# focus hitboxes preserve a real Fire TV remote graph while the underlying
# artwork remains exactly visible until a control receives focus.
home = '''<?xml version="1.0" encoding="UTF-8"?>
<window id="0">
 <defaultcontrol always="true">5001</defaultcontrol>
 <onload condition="String.IsEmpty(Skin.String(DragonMaxRealm))">Skin.SetString(DragonMaxRealm,dragon_order)</onload>
 <onload condition="String.IsEmpty(Skin.String(DragonMaxRealmName))">Skin.SetString(DragonMaxRealmName,Dragon Order)</onload>
 <controls>
  <!-- DragonMaxPrimaryArtwork: byte-identical recovered V9.2 dashboard -->
  <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height><aspectratio>stretch</aspectratio><texture>special://home/artwork/reference/dragonmax_v92_home_preview.png</texture><visible>String.IsEqual(Skin.String(DragonMaxRealm),dragon_order)</visible><animation effect="fade" start="0" end="100" time="350">WindowOpen</animation></control>
  <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height><aspectratio>stretch</aspectratio><texture>special://home/artwork/wallpapers/arcane_dominion/arcane_dominion_01.png</texture><visible>String.IsEqual(Skin.String(DragonMaxRealm),arcane_dominion)</visible></control>
  <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height><aspectratio>stretch</aspectratio><texture>special://home/artwork/wallpapers/crimson_court/crimson_court_01.png</texture><visible>String.IsEqual(Skin.String(DragonMaxRealm),crimson_court)</visible></control>
  <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height><aspectratio>stretch</aspectratio><texture>special://home/artwork/wallpapers/temple_guardians/temple_guardians_01.png</texture><visible>String.IsEqual(Skin.String(DragonMaxRealm),temple_guardians)</visible></control>
  <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height><aspectratio>stretch</aspectratio><texture>special://home/artwork/wallpapers/champion_guild/champion_guild_01.png</texture><visible>String.IsEqual(Skin.String(DragonMaxRealm),champion_guild)</visible></control>
  <control type="image"><left>0</left><top>0</top><width>1920</width><height>1080</height><aspectratio>stretch</aspectratio><texture>special://home/artwork/wallpapers/office_consortium/office_consortium_01.png</texture><visible>String.IsEqual(Skin.String(DragonMaxRealm),office_consortium)</visible></control>
  <control type="label"><left>70</left><top>54</top><width>780</width><height>80</height><font>font45</font><label>DRAGONMAX • $INFO[Skin.String(DragonMaxRealmName)]</label><textcolor>FFFFFFFF</textcolor><visible>!String.IsEqual(Skin.String(DragonMaxRealm),dragon_order)</visible></control>
  <control type="label"><left>72</left><top>128</top><width>820</width><height>46</height><font>font20</font><label>Use the left menu or choose a realm card with your remote.</label><textcolor>FFFFD27A</textcolor><visible>!String.IsEqual(Skin.String(DragonMaxRealm),dragon_order)</visible></control>

  <control type="button" id="5001"><left>4</left><top>108</top><width>190</width><height>42</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/&quot;,return)</onclick><onup>5009</onup><ondown>5002</ondown><onright>5201</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5002"><left>4</left><top>153</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=movies&quot;,return)</onclick><onup>5001</onup><ondown>5003</ondown><onright>5101</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5003"><left>4</left><top>197</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=tv&quot;,return)</onclick><onup>5002</onup><ondown>5004</ondown><onright>5101</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5004"><left>4</left><top>238</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=anime&quot;,return)</onclick><onup>5003</onup><ondown>5005</ondown><onright>5102</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5005"><left>4</left><top>279</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=music&quot;,return)</onclick><onup>5004</onup><ondown>5006</ondown><onright>5101</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5006"><left>4</left><top>319</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=sports&quot;,return)</onclick><onup>5005</onup><ondown>5007</ondown><onright>5105</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5007"><left>4</left><top>358</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=office_consortium)</onclick><onup>5006</onup><ondown>5008</ondown><onright>5106</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5008"><left>4</left><top>400</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=podcasts&quot;,return)</onclick><onup>5007</onup><ondown>5009</ondown><onright>5101</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5009"><left>4</left><top>478</top><width>190</width><height>38</height><label></label><texturefocus colordiffuse="44FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=settings&quot;,return)</onclick><onup>5008</onup><ondown>5001</ondown><onright>5101</onright><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>

  <control type="button" id="5101"><left>995</left><top>48</top><width>108</width><height>272</height><label></label><texturefocus colordiffuse="33FFD05C">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=dragon_order)</onclick><onleft>5201</onleft><onright>5102</onright><onup>5106</onup><ondown>5102</ondown><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5102"><left>1110</left><top>48</top><width>108</width><height>272</height><label></label><texturefocus colordiffuse="3343D8FF">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=arcane_dominion)</onclick><onleft>5004</onleft><onright>5103</onright><onup>5101</onup><ondown>5103</ondown><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5103"><left>1225</left><top>48</top><width>108</width><height>272</height><label></label><texturefocus colordiffuse="33F05252">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=crimson_court)</onclick><onleft>5001</onleft><onright>5104</onright><onup>5102</onup><ondown>5104</ondown><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5104"><left>1340</left><top>48</top><width>108</width><height>272</height><label></label><texturefocus colordiffuse="3392CF58">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=temple_guardians)</onclick><onleft>5001</onleft><onright>5105</onright><onup>5103</onup><ondown>5105</ondown><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5105"><left>1455</left><top>48</top><width>108</width><height>272</height><label></label><texturefocus colordiffuse="33FFCD40">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=champion_guild)</onclick><onleft>5006</onleft><onright>5106</onright><onup>5104</onup><ondown>5106</ondown><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5106"><left>1570</left><top>48</top><width>108</width><height>272</height><label></label><texturefocus colordiffuse="33D7D7D7">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>RunPlugin(plugin://plugin.program.dragonmaxportal/?action=set_realm&amp;realm=office_consortium)</onclick><onleft>5007</onleft><onright>5101</onright><onup>5105</onup><ondown>5101</ondown><animation effect="zoom" start="100" end="103" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5201"><left>215</left><top>342</top><width>300</width><height>48</height><label></label><texturefocus colordiffuse="33FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/&quot;,return)</onclick><onleft>5001</onleft><onright>5101</onright><onup>5101</onup><ondown>5202</ondown><animation effect="zoom" start="100" end="105" time="100" center="auto" reversible="true">Focus</animation></control>
  <control type="button" id="5202"><left>215</left><top>430</top><width>280</width><height>180</height><label></label><texturefocus colordiffuse="33FFA62B">common/white.png</texturefocus><texturenofocus colordiffuse="00000000">common/white.png</texturenofocus><onclick>ActivateWindow(Programs,&quot;plugin://plugin.program.dragonmaxportal/?action=open&amp;target=continue&quot;,return)</onclick><onleft>5001</onleft><onright>5101</onright><onup>5201</onup><ondown>5001</ondown><animation effect="zoom" start="100" end="104" time="100" center="auto" reversible="true">Focus</animation></control>
 </controls>
</window>'''
_base._DRAGONMAX_HOME_XML = home

from release_home import *
DEFAULT = _base._r.DEFAULT
