from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from c_api_inference import scan_c_text  # noqa: E402


class CApiInferenceTests(unittest.TestCase):
    def test_sha256_signature_and_return(self):
        source = r'''
        HB_FUNC( HB_SHA256 )
        {
           unsigned char digest[ 32 ];
           hb_sha256( hb_parcx( 1 ), hb_parclen( 1 ), digest );
           if( ! hb_parl( 2 ) )
              hb_retc( "hex" );
           else
              hb_retclen( ( char * ) digest, sizeof( digest ) );
        }
        '''
        api = scan_c_text(source)[0]
        self.assertEqual(
            "HB_SHA256( <cMessage>, [<lRaw>] )",
            api.signature,
        )
        self.assertEqual("<cDigest>", api.returns)
        self.assertEqual("Computes the SHA-256 digest of a message.", api.summary)

    def test_typed_item_parameters_and_assignment_names(self):
        source = r'''
        HB_FUNC( SAMPLE )
        {
           PHB_ITEM pArray = hb_param( 1, HB_IT_ARRAY );
           int iMode = hb_parnidef( 2, 0 );
           hb_retl( pArray != NULL && iMode > 0 );
        }
        '''
        api = scan_c_text(source)[0]
        self.assertEqual("SAMPLE( <aArray>, [<nMode>] )", api.signature)
        self.assertEqual("<lResult>", api.returns)

    def test_translate_records_target(self):
        source = "HB_FUNC_TRANSLATE( ALIAS_NAME, TARGET_NAME )\n"
        api = scan_c_text(source)[0]
        self.assertEqual("ALIAS_NAME", api.name)
        self.assertEqual("TARGET_NAME", api.target)

    def test_gc_pointer_and_custom_wrapper_parameters(self):
        source = r'''
        HB_FUNC( CURL_EASY_CLEANUP )
        {
           if( PHB_CURL_is( 1 ) )
              hb_parptrGC( &s_gcCURLFuncs, 1 );
        }
        HB_FUNC( WAPI_ISWINDOW )
        {
           hbwapi_ret_L( IsWindow( hbwapi_par_raw_HWND( 1 ) ) );
        }
        '''
        curl, window = scan_c_text(source)
        self.assertEqual("CURL_EASY_CLEANUP( <pPointer> )", curl.signature)
        self.assertEqual("WAPI_ISWINDOW( <pPointer> )", window.signature)
        self.assertEqual("<lResult>", window.returns)

    def test_commented_registration_is_ignored(self):
        source = "/* HB_FUNC( NOT_REAL ) { hb_parc( 1 ); } */\nHB_FUNC( REAL ) { hb_retni( 1 ); }"
        apis = scan_c_text(source)
        self.assertEqual(["REAL"], [api.name for api in apis])

    def test_generated_registration_macros_are_expanded(self):
        source = r'''
        #define HB_FUNC_UR_SUPER( x ) HB_FUNC( UR_SUPER_##x )
        HB_FUNC_UR_SUPER( BOF )
        {
           AREAP pArea = hb_usrGetAreaParam( 2 );
           hb_storl( HB_TRUE, 2 );
           hb_retni( 0 );
        }
        #define HB_EXPAT_SETHANDLER( a, b ) whatever
        HB_EXPAT_SETHANDLER( COMMENTHANDLER, CommentHandler )
        '''
        apis = {api.name: api for api in scan_c_text(source)}
        self.assertEqual(
            "UR_SUPER_BOF( <pArea>, <@lValue> )",
            apis["UR_SUPER_BOF"].signature,
        )
        self.assertEqual(
            "XML_SetCommentHandler( <pParser>, <bHandler> )",
            apis["XML_SetCommentHandler"].signature,
        )

    def test_local_helper_parameter_access_is_followed(self):
        source = r'''
        static void s_pad( int mode )
        {
           PHB_ITEM pValue = hb_param( 1, HB_IT_ANY );
           HB_SIZE nLength = hb_parns( 2 );
           const char * cFill = hb_parc( 3 );
        }
        HB_FUNC( HB_BPADL )
        {
           s_pad( 1 );
        }
        '''
        api = scan_c_text(source)[0]
        self.assertEqual(
            "HB_BPADL( <xValue>, <nLength>, <cFill> )",
            api.signature,
        )


if __name__ == "__main__":
    unittest.main()
