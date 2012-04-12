// based on python-tesseract by FreeToGo@gmail.com


%module tesseract
%{
#include "platform.h"
#include "publictypes.h"
#include "thresholder.h"
#include "baseapi.h"
#include "main_dummy.h"

%}
%include "platform.h"
%include "publictypes.h"
%include "thresholder.h"
%include "baseapi.h"
%include "main_dummy.h"


#define suck 100;
