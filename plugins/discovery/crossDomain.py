'''
crossDomain.py

Copyright 2006 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''

import core.controllers.outputManager as om

# options
from core.data.options.option import option
from core.data.options.optionList import optionList

from core.controllers.basePlugin.baseDiscoveryPlugin import baseDiscoveryPlugin

import core.data.kb.knowledgeBase as kb
import core.data.kb.vuln as vuln
import core.data.kb.info as info
import core.data.constants.severity as severity

import core.data.parsers.urlParser as urlParser
from core.controllers.w3afException import w3afException, w3afRunOnce


class crossDomain(baseDiscoveryPlugin):
    '''
    Analyze the crossdomain.xml file.
    @author: Andres Riancho ( andres.riancho@gmail.com )
    '''

    def __init__(self):
        baseDiscoveryPlugin.__init__(self)
        
        # Internal variables
        self._exec = True

    def discover(self, fuzzableRequest ):
        '''
        Get the crossdomain.xml file and parse it.
        
        @parameter fuzzableRequest: A fuzzableRequest instance that contains 
                                                    (among other things) the URL to test.
        '''
        dirs = []
        if not self._exec :
            # This will remove the plugin from the discovery plugins to be runned.
            raise w3afRunOnce()
            
        else:
            # Only run once
            self._exec = False
            
            is_404 = kb.kb.getData( 'error404page', '404' )
            
            base_url = urlParser.baseUrl( fuzzableRequest.getURL() )
            cross_domain_url = urlParser.urlJoin(  base_url , 'crossdomain.xml' )
            response = self._urlOpener.GET( cross_domain_url, useCache=True )
            
            if not is_404( response ):
                dirs.extend( self._createFuzzableRequests( response ) )
                
                import xml.dom.minidom
                try:
                    dom = xml.dom.minidom.parseString( response.getBody() )
                except Exception, e:
                    # Report this, it may be interesting for the final user
                    # not a vulnerability per-se... but... it's information after all
                    if 'allow-access-from' in response.getBody() or \
                    'cross-domain-policy' in response.getBody():
                        i = info.info()
                        i.setName('Invalid crossdomain.xml')
                        i.setURL( response.getURL() )
                        i.setMethod( 'GET' )
                        msg = 'The crossdomain.xml file at: "' + url  + '" is not a valid XML.'
                        i.setDesc( msg )
                        i.setId( response.id )
                        kb.kb.append( self, 'info', i )
                        om.out.information( i.getDesc() )
                else:
                    # parsed ok!
                    url_list = dom.getElementsByTagName("allow-access-from")
                    for url in url_list:
                        url = url.getAttribute('domain')
                        
                        if url == '*':
                            v = vuln.vuln()
                            v.setURL( response.getURL() )
                            v.setMethod( 'GET' )
                            v.setName( 'Insecure crossdomain.xml settings' )
                            v.setSeverity(severity.LOW)
                            msg = 'The crossdomain.xml file at "' + cross_domain_url + '" allows'
                            msg += ' flash access from any site.'
                            v.setDesc( msg )
                            v.setId( response.id )
                            kb.kb.append( self, 'vuln', v )
                            om.out.vulnerability( v.getDesc(), severity=v.getSeverity() )
                        else:
                            i = info.info()
                            i.setName('Crossdomain allow ACL')
                            i.setURL( response.getURL() )
                            i.setMethod( 'GET' )
                            i.setDesc( 'Crossdomain.xml file allows access from: "' + url  + '".')
                            i.setId( response.id )
                            kb.kb.append( self, 'info', i )
                            om.out.information( i.getDesc() )
        
        return dirs
        
    def getOptions( self ):
        '''
        @return: A list of option objects for this plugin.
        '''    
        ol = optionList()
        return ol

    def setOptions( self, OptionList ):
        '''
        This method sets all the options that are configured using the user interface 
        generated by the framework using the result of getOptions().
        
        @parameter OptionList: A dictionary with the options for the plugin.
        @return: No value is returned.
        ''' 
        pass

    def getPluginDeps( self ):
        '''
        @return: A list with the names of the plugins that should be runned before the
        current one.
        '''
        return []
        
    def getLongDesc( self ):
        '''
        @return: A DETAILED description of the plugin functions and features.
        '''
        return '''
        This plugin searches for the crossdomain.xml file used by Flash, and parses it.
        
        The crossdomain.xml file is used by Flash as an ACL that defines what domains can access
        the domain that contains the file inside the webroot. By parsing this file, you can get more
        information about relationships between sites and insecure configurations.
        '''