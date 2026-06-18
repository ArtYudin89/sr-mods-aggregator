// You can open this file in the Delphi/(Free)Pascal editor to see all of the values here in a nice tree
{$IFDEF ISPP_INVOKED}
[code]
{$ELSE}
interface
{$ENDIF}
procedure UnloadDll(S: string);
function DllGetLastError: LongInt;
Type
TComponentStateE = (csLoading, csReading, csWriting, csDestroying, csDesigning, csAncestor, csUpdating, csFixups, csFreeNotification, csInline, csDesignInstance);
Type
TComponentState = set of TComponentStateE;
Type
TRect = record Left, Top, Right, Bottom: Integer; end;
Type
TObject = class
  constructor Create;
  procedure Free;
end;
Type
TPersistent = class(TObject)
  procedure Assign(Source: TPersistent);
end;
Type
TComponent = class(TPersistent)
  function FindComponent(AName: string): TComponent;
  constructor Create(AOwner: TComponent);
  property Owner: TComponent; read write;
  procedure DestroyComponents;
  procedure Destroying;
  procedure FreeNotification(AComponent: TComponent);
  procedure InsertComponent(AComponent: TComponent);
  procedure RemoveComponent(AComponent: TComponent);
  property Components[i1: Integer]: TComponent; read;
  property ComponentCount: Integer; read;
  property ComponentIndex: Integer; read write;
  property ComponentState: Byte; read;
  property DesignInfo: LongInt; read write;
  property Name: string; read write;
  property Tag: LongInt; read write;
end;
Const
soFromBeginning = 0;// $0000
Const
soFromCurrent = 1;// $0001
Const
soFromEnd = 2;// $0002
Const
toEOF = #$0000;
Const
toSymbol = #$0001;
Const
toString = #$0002;
Const
ToInteger = #$0003;
Const
toFloat = #$0004;
Const
fmCreate = 65535;// $FFFF
Const
fmOpenRead = 0;// $0000
Const
fmOpenWrite = 1;// $0001
Const
fmOpenReadWrite = 2;// $0002
Const
fmShareCompat = 0;// $0000
Const
fmShareExclusive = 16;// $0010
Const
fmShareDenyWrite = 32;// $0020
Const
fmShareDenyRead = 48;// $0030
Const
fmShareDenyNone = 64;// $0040
Const
SecsPerDay = 86400;// $15180
Const
MSecPerDay = 86400000;// $5265C00
Const
DateDelta = 693594;// $A955A
Type
TAlignment = (taLeftJustify, taRightJustify, taCenter);
Type
THelpEvent = function (Command: Word; Data: LongInt; var CallHelp: Boolean): Boolean;
Type
TGetStrProc = procedure(const S: string);
Type
TDuplicates = (dupIgnore, dupAccept, dupError);
Type
TOperation = (opInsert, opRemove);
Type
THandle = LongInt;
Type
TNotifyEvent = procedure (Sender: TObject);
Type
TStream = class(TObject)
  function Read(Buffer: AnyString; Count: LongInt): LongInt;
  function Write(Buffer: AnyString; Count: LongInt): LongInt;
  function Seek(Offset: Int64; Origin: Word): Int64;
  procedure ReadBuffer(Buffer: AnyString; Count: LongInt);
  procedure WriteBuffer(Buffer: AnyString; Count: LongInt);
  function CopyFrom(Source: TStream; Count: Int64; BufferSize: Integer): Int64;
  property Position: LongInt; read write;
  property Size: LongInt; read write;
end;
Type
TStrings = class(TPersistent)
  constructor Create;
  function Add(S: string): Integer;
  procedure Append(S: string);
  procedure AddStrings(Strings: TStrings);
  procedure Clear;
  procedure Delete(Index: Integer);
  function IndexOf(const S: string): Integer;
  procedure Insert(Index: Integer; S: string);
  property Capacity: Integer; read write;
  property Delimiter: Char; read write;
  property StrictDelimiter: Boolean; read write;
  property DelimitedText: string; read write;
  property NameValueSeparator: Char; read write;
  property QuoteChar: Char; read write;
  property Count: Integer; read;
  property Text: string; read write;
  property CommaText: string; read write;
  procedure LoadFromFile(FileName: string);
  procedure SaveToFile(FileName: string);
  property Strings[i1: Integer]: string; read write;
  property Objects[i1: Integer]: TObject; read write;
end;
Type
TStringList = class(TStrings)
  constructor Create;
  function Find(S: string; var Index: Integer): Boolean;
  procedure Sort;
  property CaseSensitive: Boolean; read write;
  property Duplicates: TDuplicates; read write;
  property Sorted: Boolean; read write;
  property OnChange: TNotifyEvent; read write;
  property OnChanging: TNotifyEvent; read write;
end;
Type
THandleStream = class(TStream)
  constructor Create(AHandle: Integer);
  property Handle: Integer; read;
end;
Type
TFileStream = class(THandleStream)
  constructor Create(FileName: string; Mode: Word);
end;
Type
TStringStream = class(TStream)
  constructor Create(AString: string);
end;
Const
clScrollBar = -16777216;// $FF000000
Const
clBackground = -16777215;// $FF000001
Const
clActiveCaption = -16777214;// $FF000002
Const
clInactiveCaption = -16777213;// $FF000003
Const
clMenu = -16777212;// $FF000004
Const
clWindow = -16777211;// $FF000005
Const
clWindowFrame = -16777210;// $FF000006
Const
clMenuText = -16777209;// $FF000007
Const
clWindowText = -16777208;// $FF000008
Const
clCaptionText = -16777207;// $FF000009
Const
clActiveBorder = -16777206;// $FF00000A
Const
clInactiveBorder = -16777205;// $FF00000B
Const
clAppWorkSpace = -16777204;// $FF00000C
Const
clHighlight = -16777203;// $FF00000D
Const
clHighlightText = -16777202;// $FF00000E
Const
clBtnFace = -16777201;// $FF00000F
Const
clBtnShadow = -16777200;// $FF000010
Const
clGrayText = -16777199;// $FF000011
Const
clBtnText = -16777198;// $FF000012
Const
clInactiveCaptionText = -16777197;// $FF000013
Const
clBtnHighlight = -16777196;// $FF000014
Const
cl3DDkShadow = -16777195;// $FF000015
Const
cl3DLight = -16777194;// $FF000016
Const
clInfoText = -16777193;// $FF000017
Const
clInfoBk = -16777192;// $FF000018
Const
clBlack = 0;// $0000
Const
clMaroon = 128;// $0080
Const
clGreen = 32768;// $8000
Const
clOlive = 32896;// $8080
Const
clNavy = 8388608;// $800000
Const
clPurple = 8388736;// $800080
Const
clTeal = 8421376;// $808000
Const
clGray = 8421504;// $808080
Const
clSilver = 12632256;// $C0C0C0
Const
clRed = 255;// $00FF
Const
clLime = 65280;// $FF00
Const
clYellow = 65535;// $FFFF
Const
clBlue = 16711680;// $FF0000
Const
clFuchsia = 16711935;// $FF00FF
Const
clAqua = 16776960;// $FFFF00
Const
clLtGray = 12632256;// $C0C0C0
Const
clDkGray = 8421504;// $808080
Const
clWhite = 16777215;// $FFFFFF
Const
clNone = 536870911;// $1FFFFFFF
Const
clDefault = 536870912;// $20000000
Type
TFontStyle = (fsBold, fsItalic, fsUnderline, fsStrikeOut);
Type
TFontStyles = set of TFontStyle;
Type
TFontPitch = (fpDefault, fpVariable, fpFixed);
Type
TPenStyle = (psSolid, psDash, psDot, psDashDot, psDashDotDot, psClear, psInsideFrame);
Type
TPenMode = (pmBlack, pmWhite, pmNop, pmNot, pmCopy, pmNotCopy, pmMergePenNot, pmMaskPenNot, pmMergeNotPen, pmMaskNotPen, pmMerge, pmNotMerge, pmMask, pmNotMask, pmXor, pmNotXor);
Type
TBrushStyle = (bsSolid, bsClear, bsHorizontal, bsVertical, bsFDiagonal, bsBDiagonal, bsCross, bsDiagCross);
Type
TColor = Integer;
Type
HBITMAP = Integer;
Type
HPALETTE = Integer;
Const
clHotLight = -16777190;// $FF00001A
Type
TGraphicsObject = class(TPersistent)
  property OnChange: TNotifyEvent; read write;
end;
Type
TFont = class(TGraphicsObject)
  constructor Create;
  property Handle: Integer; read write;
  property Color: TColor; read write;
  property Height: Integer; read write;
  property Name: string; read write;
  property Pitch: Byte; read write;
  property Size: Integer; read write;
  property PixelsPerInch: Integer; read write;
  property Style: TFontStyles; read write;
end;
Type
TPen = class(TGraphicsObject)
  constructor Create;
  property Color: TColor; read write;
  property Mode: TPenMode; read write;
  property Style: TPenStyle; read write;
  property Width: Integer; read write;
end;
Type
TBrush = class(TGraphicsObject)
  constructor Create;
  property Color: TColor; read write;
  property Style: TBrushStyle; read write;
end;
Type
TCanvas = class(TPersistent)
  procedure Arc(X1, Y1, X2, Y2, X3, Y3, X4, Y4: Integer);
  procedure Chord(X1, Y1, X2, Y2, X3, Y3, X4, Y4: Integer);
  procedure Draw(X, Y: Integer; Graphic: TGraphic);
  procedure Ellipse(X1, Y1, X2, Y2: Integer);
  procedure FillRect(const Rect: TRect);
  procedure FloodFill(X, Y: Integer; Color: TColor; FillStyle: Byte);
  procedure LineTo(X, Y: Integer);
  procedure MoveTo(X, Y: Integer);
  procedure Pie(X1, Y1, X2, Y2, X3, Y3, X4, Y4: Integer);
  procedure Rectangle(X1, Y1, X2, Y2: Integer);
  procedure Refresh;
  procedure RoundRect(X1, Y1, X2, Y2, X3, Y3: Integer);
  function TextHeight(Text: string): Integer;
  procedure TextOut(X, Y: Integer; Text: string);
  function TextWidth(Text: string): Integer;
  property Handle: Integer; read write;
  property Pixels[i1: Integer; i2: Integer]: Integer; read write;
  property Brush: TBrush; read;
  property CopyMode: Byte; read write;
  property Font: TFont; read;
  property Pen: TPen; read;
end;
Type
TGraphic = class(TPersistent)
  constructor Create;
  procedure LoadFromFile(const FileName: string);
  procedure SaveToFile(const FileName: string);
  property Empty: Boolean; read;
  property Height: Integer; read write;
  property Modified: Boolean; read write;
  property Width: Integer; read write;
  property OnChange: TNotifyEvent; read write;
end;
Type
TBitmap = class(TGraphic)
  procedure LoadFromStream(Stream: TStream);
  procedure SaveToStream(Stream: TStream);
  property Canvas: TCanvas; read;
  property Handle: HBITMAP; read write;
  procedure Dormant;
  procedure FreeImage;
  procedure LoadFromClipboardFormat(AFormat: Word; AData: THandle; APalette: HPALETTE);
  procedure LoadFromResourceName(Instance: THandle; const ResName: string);
  procedure LoadFromResourceID(Instance: THandle; ResID: Integer);
  function ReleaseHandle: HBITMAP;
  function ReleasePalette: HPALETTE;
  procedure SaveToClipboardFormat(var Format: Word; var Data: THandle; var APalette: HPALETTE);
  property Monochrome: Boolean; read write;
  property Palette: HPALETTE; read write;
  property IgnorePalette: Boolean; read write;
  property TransparentColor: TColor; read;
  property AlphaFormat: TAlphaFormat; read write;
end;
Type
TEShiftState = (ssShift, ssAlt, ssCtrl, ssLeft, ssRight, ssMiddle, ssDouble);
Type
TShiftState = set of TEShiftState;
Type
TMouseButton = (mbLeft, mbRight, mbMiddle);
Type
TDragMode = (dmManual, dmAutomatic);
Type
TDragState = (dsDragEnter, dsDragLeave, dsDragMove);
Type
TDragKind = (dkDrag, dkDock);
Type
TMouseEvent = procedure (Sender: TObject; Button: TMouseButton; Shift: TShiftState; X, Y: Integer);
Type
TMouseMoveEvent = procedure(Sender: TObject; Shift: TShiftState; X, Y: Integer);
Type
TKeyEvent = procedure (Sender: TObject; var Key: Word; Shift: TShiftState);
Type
TKeyPressEvent = procedure(Sender: TObject; var Key: Char);
Type
TDragOverEvent = procedure(Sender, Source: TObject; X, Y: Integer; State: TDragState; var Accept: Boolean);
Type
TDragDropEvent = procedure(Sender, Source: TObject; X, Y: Integer);
Type
HWND = LongInt;
Type
TEndDragEvent = procedure(Sender, Target: TObject; X, Y: Integer);
Type
TAlign = (alNone, alTop, alBottom, alLeft, alRight, alClient);
Type
TAnchorKind = (akLeft, akTop, akRight, akBottom);
Type
TAnchors = set of TAnchorKind;
Type
TModalResult = Integer;
Type
TCursor = Integer;
Type
TPoint = record X,Y: LongInt; end;
Const
mrNone = 0;// $0000
Const
mrOk = 1;// $0001
Const
mrCancel = 2;// $0002
Const
mrAbort = 3;// $0003
Const
mrRetry = 4;// $0004
Const
mrIgnore = 5;// $0005
Const
mrYes = 6;// $0006
Const
mrNo = 7;// $0007
Const
mrAll = 8;// $0008
Const
mrNoToAll = 9;// $0009
Const
mrYesToAll = 10;// $000A
Const
crDefault = 0;// $0000
Const
crNone = -1;// $FFFFFFFF
Const
crArrow = -2;// $FFFFFFFE
Const
crCross = -3;// $FFFFFFFD
Const
crIBeam = -4;// $FFFFFFFC
Const
crSizeNESW = -6;// $FFFFFFFA
Const
crSizeNS = -7;// $FFFFFFF9
Const
crSizeNWSE = -8;// $FFFFFFF8
Const
crSizeWE = -9;// $FFFFFFF7
Const
crUpArrow = -10;// $FFFFFFF6
Const
crHourGlass = -11;// $FFFFFFF5
Const
crDrag = -12;// $FFFFFFF4
Const
crNoDrop = -13;// $FFFFFFF3
Const
crHSplit = -14;// $FFFFFFF2
Const
crVSplit = -15;// $FFFFFFF1
Const
crMultiDrag = -16;// $FFFFFFF0
Const
crSQLWait = -17;// $FFFFFFEF
Const
crNo = -18;// $FFFFFFEE
Const
crAppStart = -19;// $FFFFFFED
Const
crHelp = -20;// $FFFFFFEC
Const
crHandPoint = -21;// $FFFFFFEB
Const
crSizeAll = -22;// $FFFFFFEA
Type
TBevelKind = (bkNone, bkTile, bkSoft, bkFlat);
Type
TDragObject = class(TObject)
end;
Type
TStartDragEvent = procedure (Sender: TObject; var DragObject: TDragObject);
Type
TConstraintSize = Integer;
Type
TSizeConstraints = class(TPersistent)
  property MaxHeight: TConstraintSize; read write;
  property MaxWidth: TConstraintSize; read write;
  property MinHeight: TConstraintSize; read write;
  property MinWidth: TConstraintSize; read write;
end;
Type
TControl = class(TComponent)
  constructor Create(AOwner: TComponent);
  procedure BringToFront;
  procedure Hide;
  procedure Invalidate;
  procedure Refresh;
  procedure Repaint;
  procedure SendToBack;
  procedure Show;
  procedure Update;
  procedure SetBounds(X,Y,w,h: Integer);
  property Left: Integer; read write;
  property Top: Integer; read write;
  property Width: Integer; read write;
  property Height: Integer; read write;
  property Hint: string; read write;
  property Align: TAlign; read write;
  property ClientHeight: LongInt; read write;
  property ClientWidth: LongInt; read write;
  property ShowHint: Boolean; read write;
  property Visible: Boolean; read write;
  property Enabled: Boolean; read write;
  property Cursor: TCursor; read write;
  property Parent: TWinControl; read write;
end;
Type
TWinControl = class(TControl)
  property Handle: LongInt; read;
  property Showing: Boolean; read;
  property TabOrder: Integer; read write;
  property TabStop: Boolean; read write;
  function CanFocus: Boolean;
  function Focused: Boolean;
  property Controls[i1: Integer]: TControl; read;
  property ControlCount: Integer; read;
  property ParentBackground: Boolean; read write;
end;
Type
TGraphicControl = class(TControl)
end;
Type
TCustomControl = class(TWinControl)
end;
Type
TIdleEvent = procedure (Sender: TObject; var Done: Boolean);
Type
TScrollBarKind = (sbHorizontal, sbVertical);
Type
TScrollBarInc = SmallInt;
Type
TFormBorderStyle = (bsNone, bsSingle, bsSizeable, bsDialog, bsToolWindow, bsSizeToolWin);
Type
TBorderStyle = TFormBorderStyle;
Type
TWindowState = (wsNormal, wsMinimized, wsMaximized);
Type
TFormStyle = (fsNormal, fsMDIChild, fsMDIForm, fsStayOnTop);
Type
TPopupMode = (pmNone, pmAuto, pmExplicit);
Type
TPosition = (poDesigned, poDefault, poDefaultPosOnly, poDefaultSizeOnly, poScreenCenter, poDesktopCenter, poMainFormCenter, poOwnerFormCenter);
Type
TPrintScale = (poNone, poProportional, poPrintToFit);
Type
TCloseAction = (caNone, caHide, caFree, caMinimize);
Type
TCloseEvent = procedure(Sender: TObject; var Action: TCloseAction);
Type
TCloseQueryEvent = procedure(Sender: TObject; var CanClose: Boolean);
Type
TBorderIcon = (biSystemMenu, biMinimize, biMaximize, biHelp);
Type
TBorderIcons = set of TBorderIcon;
Type
THelpContext = LongInt;
Type
TScrollingWinControl = class(TWinControl)
  procedure ScrollInView(AControl: TControl);
  property HorzScrollBar: TControlScrollBar; read write;
  property VertScrollBar: TControlScrollBar; read write;
end;
Type
TForm = class(TScrollingWinControl)
  constructor CreateNew(AOwner: TComponent; Dummy: Integer);
  procedure Close;
  procedure Hide;
  procedure Show;
  function ShowModal: Integer;
  procedure Release;
  property Active: Boolean; read;
  property ActiveControl: TWinControl; read write;
  property Anchors: TAnchors; read write;
  property Constraints: TSizeConstraints; read write;
  property BorderIcons: TBorderIcons; read write;
  property BorderStyle: TFormBorderStyle; read write;
  property Caption: NativeString; read write;
  property AutoScroll: Boolean; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property FormStyle: TFormStyle; read write;
  property KeyPreview: Boolean; read write;
  property PopupMode: TPopupMode; read write;
  property PopupParent: TForm; read write;
  property Position: TPosition; read write;
  property OnActivate: TNotifyEvent; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnClose: TCloseEvent; read write;
  property OnCloseQuery: TCloseQueryEvent; read write;
  property OnCreate: TNotifyEvent; read write;
  property OnDestroy: TNotifyEvent; read write;
  property OnDeactivate: TNotifyEvent; read write;
  property OnHide: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
  property OnResize: TNotifyEvent; read write;
  property OnShow: TNotifyEvent; read write;
end;
Type
TEditCharCase = (ecNormal, ecUpperCase, ecLowerCase);
Type
TScrollStyle = (ssNone, ssHorizontal, ssVertical, ssBoth);
Type
TComboBoxStyle = (csDropDown, csSimple, csDropDownList, csOwnerDrawFixed, csOwnerDrawVariable);
Type
TDrawItemEvent = procedure(Control: TWinControl; Index: Integer; Rect: TRect; State: Byte);
Type
TMeasureItemEvent = procedure(Control: TWinControl; Index: Integer; var Height: Integer);
Type
TCheckBoxState = (cbUnchecked, cbChecked, cbGrayed);
Type
TListBoxStyle = (lbStandard, lbOwnerDrawFixed, lbOwnerDrawVariable);
Type
TScrollCode = (scLineUp, scLineDown, scPageUp, scPageDown, scPosition, scTrack, scTop, scBottom, scEndScroll);
Type
TScrollEvent = procedure(Sender: TObject; ScrollCode: TScrollCode; var ScrollPos: Integer);
Type
TEOwnerDrawState = (odSelected, odGrayed, odDisabled, odChecked, odFocused, odDefault, odHotLight, odInactive, odNoAccel, odNoFocusRect, odReserved1, odReserved2, odComboBoxEdit);
Type
TTextLayout = (tlTop, tlCenter, tlBottom);
Type
TOwnerDrawState = set of TEOwnerDrawState;
Type
TCustomLabel = class(TGraphicControl)
end;
Type
TLabel = class(TCustomLabel)
  property Alignment: TAlignment; read write;
  property Anchors: TAnchors; read write;
  property AutoSize: Boolean; read write;
  property Caption: string; read write;
  property Color: TColor; read write;
  property DragCursor: LongInt; read write;
  property DragMode: TDragMode; read write;
  property FocusControl: TWinControl; read write;
  property Font: TFont; read write;
  property Layout: TTextLayout; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property ParentShowHint: Boolean; read write;
  property ShowAccelChar: Boolean; read write;
  property Transparent: Boolean; read write;
  property WordWrap: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnDragDrop: TDragDropEvent; read write;
  property OnDragOver: TDragOverEvent; read write;
  property OnEndDrag: TEndDragEvent; read write;
  property OnMouseDown: TMouseEvent; read write;
  property OnMouseMove: TMouseMoveEvent; read write;
  property OnMouseUp: TMouseEvent; read write;
  property OnStartDrag: TStartDragEvent; read write;
end;
Type
TCustomEdit = class(TWinControl)
  procedure Clear;
  procedure ClearSelection;
  procedure SelectAll;
  property Modified: Boolean; read write;
  property SelLength: Integer; read write;
  property SelStart: Integer; read write;
  property SelText: string; read write;
  property Text: string; read write;
end;
Type
TEdit = class(TCustomEdit)
  property Anchors: TAnchors; read write;
  property AutoSelect: Boolean; read write;
  property AutoSize: Boolean; read write;
  property BorderStyle: TBorderStyle; read write;
  property CharCase: TEditCharCase; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property HideSelection: Boolean; read write;
  property MaxLength: Integer; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property PasswordChar: Char; read write;
  property ReadOnly: Boolean; read write;
  property Text: string; read write;
  property OnChange: TNotifyEvent; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
end;
Type
TCustomMemo = class(TCustomEdit)
  property Lines: TStrings; read write;
end;
Type
TMemo = class(TCustomMemo)
  property Anchors: TAnchors; read write;
  property Alignment: TAlignment; read write;
  property BorderStyle: TBorderStyle; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property HideSelection: Boolean; read write;
  property MaxLength: Integer; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property ReadOnly: Boolean; read write;
  property ScrollBars: TScrollStyle; read write;
  property WantReturns: Boolean; read write;
  property WantTabs: Boolean; read write;
  property WordWrap: Boolean; read write;
  property OnChange: TNotifyEvent; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
end;
Type
TCustomComboBox = class(TWinControl)
  property DroppedDown: Boolean; read write;
  property Items: TStrings; read write;
  property ItemIndex: Integer; read write;
end;
Type
TComboBox = class(TCustomComboBox)
  property Style: TComboBoxStyle; read write;
  property Anchors: TAnchors; read write;
  property Color: TColor; read write;
  property DropDownCount: Integer; read write;
  property Font: TFont; read write;
  property MaxLength: Integer; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property Sorted: Boolean; read write;
  property Text: string; read write;
  property OnChange: TNotifyEvent; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnDropDown: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
end;
Type
TButtonControl = class(TWinControl)
end;
Type
TButton = class(TButtonControl)
  property Anchors: TAnchors; read write;
  property Cancel: Boolean; read write;
  property Caption: string; read write;
  property Default: Boolean; read write;
  property Font: TFont; read write;
  property ModalResult: LongInt; read write;
  property ParentFont: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
end;
Type
TCustomCheckBox = class(TButtonControl)
end;
Type
TCheckBox = class(TCustomCheckBox)
  property Alignment: TAlignment; read write;
  property AllowGrayed: Boolean; read write;
  property Anchors: TAnchors; read write;
  property Caption: string; read write;
  property Checked: Boolean; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property State: TCheckBoxState; read write;
  property OnClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
end;
Type
TRadioButton = class(TButtonControl)
  property Alignment: TAlignment; read write;
  property Anchors: TAnchors; read write;
  property Caption: string; read write;
  property Checked: Boolean; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
end;
Type
TCustomListBox = class(TWinControl)
  property Items: TStrings; read write;
  property ItemIndex: Integer; read write;
  property SelCount: Integer; read;
  property Selected[i1: Integer]: Boolean; read write;
end;
Type
TListBox = class(TCustomListBox)
  property Anchors: TAnchors; read write;
  property BorderStyle: TBorderStyle; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property MultiSelect: Boolean; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property Sorted: Boolean; read write;
  property Style: TListBoxStyle; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
end;
Type
TShapeType = (stRectangle, stSquare, stRoundRect, stRoundSquare, stEllipse, stCircle);
Type
TBevelStyle = (bsLowered, bsRaised);
Type
TBevelShape = (bsBox, bsFrame, bsTopLine, bsBottomLine, bsLeftLine, bsRightLine,bsSpacer);
Type
TPanelBevel = (bvNone, bvLowered, bvRaised,bvSpace);
Type
TBevelWidth = LongInt;
Type
TBorderWidth = LongInt;
Type
TSectionEvent = procedure(Sender: TObject; ASection, AWidth: Integer);
Type
TSysLinkType = (sltURL, sltID);
Type
TSysLinkEvent = procedure(Sender: TObject; const Link: string; LinkType: TSysLinkType);
Type
TBevel = class(TGraphicControl)
  property Anchors: TAnchors; read write;
  property Shape: TBevelShape; read write;
  property Style: TBevelStyle; read write;
end;
Type
TCustomPanel = class(TCustomControl)
end;
Type
TPanel = class(TCustomPanel)
  property Alignment: TAlignment; read write;
  property Anchors: TAnchors; read write;
  property BevelInner: TPanelBevel; read write;
  property BevelOuter: TPanelBevel; read write;
  property BevelKind: TBevelKind; read write;
  property BevelWidth: TBevelWidth; read write;
  property BorderWidth: TBorderWidth; read write;
  property BorderStyle: TBorderStyle; read write;
  property Caption: string; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
end;
Type
TCustomLinkLabel = class(TWinControl)
  property Alignment: TAlignment; read write;
  property AutoSize: Boolean; read write;
  property UseVisualStyle: Boolean; read write;
  property OnLinkClick: TSysLinkEvent; read write;
end;
Type
TLinkLabel = class(TCustomLinkLabel)
  property Anchors: TAnchors; read write;
  property Caption: string; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
end;
Type
HResult = LongInt;
Type
TGUID = record D1: LongWord; D2: Word; D3: Word; D4: array[0..7] of Byte; end;
Type
TCLSID = TGUID;
Type
TIID = TGUID;
procedure OleCheck(Result: HResult);
function StringToGUID(const S: string): TGUID;
function CreateComObject(const ClassID: TGUID): IUnknown;
function CreateOleObject(const ClassName: string): IDispatch;
function GetActiveOleObject(const ClassName: string): IDispatch;
Type
TNewStaticText = class(TWinControl)
  function AdjustHeight: Integer;
  property Anchors: TAnchors; read write;
  property AutoSize: Boolean; read write;
  property Caption: String; read write;
  property Color: TColor; read write;
  property FocusControl: TWinControl; read write;
  property Font: TFont; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property ShowAccelChar: Boolean; read write;
  property WordWrap: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
end;
Type
TCheckItemOperation = (coUncheck, coCheck, coCheckWithChildren);
Type
TNewCheckListBox = class(TCustomListBox)
  function AddCheckBox(const ACaption, ASubItem: String; ALevel: Byte; AChecked, AEnabled, AHasInternalChildren, ACheckWhenParentChecked: Boolean; AObject: TObject): Integer;
  function AddGroup(const ACaption, ASubItem: String; ALevel: Byte; AObject: TObject): Integer;
  function AddRadioButton(const ACaption, ASubItem: String; ALevel: Byte; AChecked, AEnabled: Boolean; AObject: TObject): Integer;
  function CheckItem(const Index: Integer; const AOperation: TCheckItemOperation): Boolean;
  property Anchors: TAnchors; read write;
  property Checked[i1: Integer]: Boolean; read write;
  property State[i1: Integer]: TCheckBoxState; read;
  property ItemCaption[i1: Integer]: String; read write;
  property ItemEnabled[i1: Integer]: Boolean; read write;
  property ItemLevel[i1: Integer]: Byte; read;
  property ItemObject[i1: Integer]: TObject; read write;
  property ItemSubItem[i1: Integer]: String; read write;
  property ItemFontStyle[i1: Integer]: TFontStyles; read write;
  property SubItemFontStyle[i1: Integer]: TFontStyles; read write;
  property Flat: Boolean; read write;
  property MinItemHeight: Integer; read write;
  property Offset: Integer; read write;
  property OnClickCheck: TNotifyEvent; read write;
  property BorderStyle: TBorderStyle; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
  property ShowLines: Boolean; read write;
  property WantTabs: Boolean; read write;
  property RequireRadioSelection: Boolean; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
end;
Type
TNewProgressBarState = (npbsNormal, npbsError, npbsPaused);
Type
TNewProgressBarStyle = (npbstNormal, npbstMarquee);
Type
TNewProgressBar = class(TWinControl)
  property Anchors: TAnchors; read write;
  property Min: Longint; read write;
  property Max: Longint; read write;
  property Position: Longint; read write;
  property State: TNewProgressBarState; read write;
  property Style: TNewProgressBarStyle; read write;
end;
Type
TRichEditViewer = class(TMemo)
  property Anchors: TAnchors; read write;
  property BevelKind: TBevelKind; read write;
  property BorderStyle: TBorderStyle; read write;
  property RTFText: AnsiString; write;
  property UseRichEdit: Boolean; read write;
end;
Type
TPasswordEdit = class(TCustomEdit)
  property Anchors: TAnchors; read write;
  property AutoSelect: Boolean; read write;
  property AutoSize: Boolean; read write;
  property BorderStyle: TBorderStyle; read write;
  property Color: TColor; read write;
  property Font: TFont; read write;
  property HideSelection: Boolean; read write;
  property MaxLength: Integer; read write;
  property ParentColor: Boolean; read write;
  property ParentFont: Boolean; read write;
  property Password: Boolean; read write;
  property ReadOnly: Boolean; read write;
  property Text: string; read write;
  property OnChange: TNotifyEvent; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
  property OnKeyDown: TKeyEvent; read write;
  property OnKeyPress: TKeyPressEvent; read write;
  property OnKeyUp: TKeyEvent; read write;
  property OnEnter: TNotifyEvent; read write;
  property OnExit: TNotifyEvent; read write;
end;
Type
TCustomFolderTreeView = class(TWinControl)
  procedure ChangeDirectory(const Value: String; const CreateNewItems: Boolean);
  procedure CreateNewDirectory(const ADefaultName: String);
  property Directory: String; read write;
end;
Type
TFolderRenameEvent = procedure(Sender: TCustomFolderTreeView; var NewName: String; var Accept: Boolean);
Type
TFolderTreeView = class(TCustomFolderTreeView)
  property Anchors: TAnchors; read write;
  property OnChange: TNotifyEvent; read write;
  property OnRename: TFolderRenameEvent; read write;
end;
Type
TStartMenuFolderTreeView = class(TCustomFolderTreeView)
  procedure SetPaths(const AUserPrograms, ACommonPrograms, AUserStartup, ACommonStartup: String);
  property Anchors: TAnchors; read write;
  property OnChange: TNotifyEvent; read write;
  property OnRename: TFolderRenameEvent; read write;
end;
Type
TAlphaFormat = (afIgnored, afDefined, afPremultiplied);
Type
TBitmapImage = class(TGraphicControl)
  property Anchors: TAnchors; read write;
  property AutoSize: Boolean; read write;
  property BackColor: TColor; read write;
  property Center: Boolean; read write;
  property Bitmap: TBitmap; read write;
  property ReplaceColor: TColor; read write;
  property ReplaceWithColor: TColor; read write;
  property Stretch: Boolean; read write;
  property OnClick: TNotifyEvent; read write;
  property OnDblClick: TNotifyEvent; read write;
end;
Type
TNewEdit = class(TEdit)
end;
Type
TNewMemo = class(TMemo)
end;
Type
TNewComboBox = class(TComboBox)
end;
Type
TNewListBox = class(TListBox)
end;
Type
TNewButton = class(TButton)
end;
Type
TNewCheckBox = class(TCheckBox)
end;
Type
TNewRadioButton = class(TRadioButton)
end;
Type
TNewLinkLabel = class(TLinkLabel)
  function AdjustHeight: Integer;
end;
Type
TNewNotebookPage = class(TCustomControl)
  property Color: TColor; read write;
  property Notebook: TNewNotebook; read write;
  property PageIndex: Integer; read write;
end;
Type
TNewNotebook = class(TWinControl)
  function FindNextPage(CurPage: TNewNotebookPage; GoForward: Boolean): TNewNotebookPage;
  property Anchors: TAnchors; read write;
  property PageCount: Integer; read;
  property Pages[i1: Integer]: TNewNotebookPage; read;
  property ActivePage: TNewNotebookPage; read write;
end;
Type
TUIStateForm = class(TForm)
end;
Type
TSetupForm = class(TUIStateForm)
  function CalculateButtonWidth(const ButtonCaptions: array of String): Integer;
  function ShouldSizeX: Boolean;
  function ShouldSizeY: Boolean;
  procedure FlipSizeAndCenterIfNeeded(const ACenterInsideControl: Boolean; const CenterInsideControlCtl: TWinControl; const CenterInsideControlInsideClientArea: Boolean);
  property ControlsFlipped: Boolean; read;
  property FlipControlsOnShow: Boolean; read write;
  property KeepSizeY: Boolean; read write;
  property RightToLeft: Boolean; read;
  property SizeAndCenterOnShow: Boolean; read write;
end;
Type
TWizardForm = class(TSetupForm)
  property CancelButton: TNewButton; read;
  property NextButton: TNewButton; read;
  property BackButton: TNewButton; read;
  property OuterNotebook: TNewNotebook; read;
  property InnerNotebook: TNewNotebook; read;
  property WelcomePage: TNewNotebookPage; read;
  property InnerPage: TNewNotebookPage; read;
  property FinishedPage: TNewNotebookPage; read;
  property LicensePage: TNewNotebookPage; read;
  property PasswordPage: TNewNotebookPage; read;
  property InfoBeforePage: TNewNotebookPage; read;
  property UserInfoPage: TNewNotebookPage; read;
  property SelectDirPage: TNewNotebookPage; read;
  property SelectComponentsPage: TNewNotebookPage; read;
  property SelectProgramGroupPage: TNewNotebookPage; read;
  property SelectTasksPage: TNewNotebookPage; read;
  property ReadyPage: TNewNotebookPage; read;
  property PreparingPage: TNewNotebookPage; read;
  property InstallingPage: TNewNotebookPage; read;
  property InfoAfterPage: TNewNotebookPage; read;
  property DiskSpaceLabel: TNewStaticText; read;
  property DirEdit: TEdit; read;
  property GroupEdit: TNewEdit; read;
  property NoIconsCheck: TNewCheckBox; read;
  property PasswordLabel: TNewStaticText; read;
  property PasswordEdit: TPasswordEdit; read;
  property PasswordEditLabel: TNewStaticText; read;
  property ReadyMemo: TNewMemo; read;
  property TypesCombo: TNewComboBox; read;
  property Bevel: TBevel; read;
  property WizardBitmapImage: TBitmapImage; read;
  property WelcomeLabel1: TNewStaticText; read;
  property InfoBeforeMemo: TRichEditViewer; read;
  property InfoBeforeClickLabel: TNewStaticText; read;
  property MainPanel: TPanel; read;
  property Bevel1: TBevel; read;
  property PageNameLabel: TNewStaticText; read;
  property PageDescriptionLabel: TNewStaticText; read;
  property WizardSmallBitmapImage: TBitmapImage; read;
  property ReadyLabel: TNewStaticText; read;
  property FinishedLabel: TNewStaticText; read;
  property YesRadio: TNewRadioButton; read;
  property NoRadio: TNewRadioButton; read;
  property WizardBitmapImage2: TBitmapImage; read;
  property WelcomeLabel2: TNewStaticText; read;
  property LicenseLabel1: TNewStaticText; read;
  property LicenseMemo: TRichEditViewer; read;
  property InfoAfterMemo: TRichEditViewer; read;
  property InfoAfterClickLabel: TNewStaticText; read;
  property ComponentsList: TNewCheckListBox; read;
  property ComponentsDiskSpaceLabel: TNewStaticText; read;
  property BeveledLabel: TNewStaticText; read;
  property StatusLabel: TNewStaticText; read;
  property FilenameLabel: TNewStaticText; read;
  property ProgressGauge: TNewProgressBar; read;
  property SelectDirLabel: TNewStaticText; read;
  property SelectStartMenuFolderLabel: TNewStaticText; read;
  property SelectComponentsLabel: TNewStaticText; read;
  property SelectTasksLabel: TNewStaticText; read;
  property LicenseAcceptedRadio: TNewRadioButton; read;
  property LicenseNotAcceptedRadio: TNewRadioButton; read;
  property UserInfoNameLabel: TNewStaticText; read;
  property UserInfoNameEdit: TNewEdit; read;
  property UserInfoOrgLabel: TNewStaticText; read;
  property UserInfoOrgEdit: TNewEdit; read;
  property PreparingErrorBitmapImage: TBitmapImage; read;
  property PreparingLabel: TNewStaticText; read;
  property FinishedHeadingLabel: TNewStaticText; read;
  property UserInfoSerialLabel: TNewStaticText; read;
  property UserInfoSerialEdit: TNewEdit; read;
  property TasksList: TNewCheckListBox; read;
  property RunList: TNewCheckListBox; read;
  property DirBrowseButton: TNewButton; read;
  property GroupBrowseButton: TNewButton; read;
  property SelectDirBitmapImage: TBitmapImage; read;
  property SelectGroupBitmapImage: TBitmapImage; read;
  property SelectDirBrowseLabel: TNewStaticText; read;
  property SelectStartMenuFolderBrowseLabel: TNewStaticText; read;
  property PreparingYesRadio: TNewRadioButton; read;
  property PreparingNoRadio: TNewRadioButton; read;
  property PreparingMemo: TNewMemo; read;
  property CurPageID: Integer; read;
  function AdjustLabelHeight(ALabel: TNewStaticText): Integer;
  function AdjustLinkLabelHeight(ALinkLabel: TNewLinkLabel): Integer;
  procedure IncTopDecHeight(AControl: TControl; Amount: Integer);
  property PrevAppDir: String; read;
end;
Type
TUninstallProgressForm = class(TSetupForm)
  property OuterNotebook: TNewNotebook; read;
  property InnerPage: TNewNotebookPage; read;
  property InnerNotebook: TNewNotebook; read;
  property InstallingPage: TNewNotebookPage; read;
  property MainPanel: TPanel; read;
  property PageNameLabel: TNewStaticText; read;
  property PageDescriptionLabel: TNewStaticText; read;
  property WizardSmallBitmapImage: TBitmapImage; read;
  property Bevel1: TBevel; read;
  property StatusLabel: TNewStaticText; read;
  property ProgressBar: TNewProgressBar; read;
  property BeveledLabel: TNewStaticText; read;
  property Bevel: TBevel; read;
  property CancelButton: TNewButton; read;
end;
Type
TWizardPage = class(TComponent)
  property ID: Integer; read;
  property Caption: String; read write;
  property Description: String; read write;
  property Surface: TNewNotebookPage; read;
  property SurfaceColor: TColor; read;
  property SurfaceHeight: Integer; read;
  property SurfaceWidth: Integer; read;
  property OnActivate: TWizardPageNotifyEvent; read write;
  property OnBackButtonClick: TWizardPageButtonEvent; read write;
  property OnCancelButtonClick: TWizardPageCancelEvent; read write;
  property OnNextButtonClick: TWizardPageButtonEvent; read write;
  property OnShouldSkipPage: TWizardPageShouldSkipEvent; read write;
end;
Type
TWizardPageNotifyEvent = procedure(Sender: TWizardPage);
Type
TWizardPageButtonEvent = function(Sender: TWizardPage): Boolean;
Type
TWizardPageCancelEvent = procedure(Sender: TWizardPage; var ACancel, AConfirm: Boolean);
Type
TWizardPageShouldSkipEvent = function(Sender: TWizardPage): Boolean;
Type
TInputQueryWizardPage = class(TWizardPage)
  function Add(const APrompt: String; const APassword: Boolean): Integer;
  property Edits[i1: Integer]: TPasswordEdit; read;
  property PromptLabels[i1: Integer]: TNewStaticText; read;
  property SubCaptionLabel: TNewStaticText; read;
  property Values[i1: Integer]: String; read write;
end;
Type
TInputOptionWizardPage = class(TWizardPage)
  function Add(const ACaption: String): Integer;
  function AddEx(const ACaption: String; const ALevel: Byte; const AExclusive: Boolean): Integer;
  property CheckListBox: TNewCheckListBox; read;
  property SelectedValueIndex: Integer; read write;
  property SubCaptionLabel: TNewStaticText; read;
  property Values[i1: Integer]: Boolean; read write;
end;
Type
TInputDirWizardPage = class(TWizardPage)
  function Add(const APrompt: String): Integer;
  property Buttons[i1: Integer]: TNewButton; read;
  property Edits[i1: Integer]: TEdit; read;
  property NewFolderName: String; read write;
  property PromptLabels[i1: Integer]: TNewStaticText; read;
  property SubCaptionLabel: TNewStaticText; read;
  property Values[i1: Integer]: String; read write;
end;
Type
TInputFileWizardPage = class(TWizardPage)
  function Add(const APrompt, AFilter, ADefaultExtension: String): Integer;
  property Buttons[i1: Integer]: TNewButton; read;
  property Edits[i1: Integer]: TEdit; read;
  property PromptLabels[i1: Integer]: TNewStaticText; read;
  property SubCaptionLabel: TNewStaticText; read;
  property Values[i1: Integer]: String; read write;
  property IsSaveButton[i1: Integer]: Boolean; read write;
end;
Type
TOutputMsgWizardPage = class(TWizardPage)
  property MsgLabel: TNewStaticText; read;
end;
Type
TOutputMsgMemoWizardPage = class(TWizardPage)
  property RichEditViewer: TRichEditViewer; read;
  property SubCaptionLabel: TNewStaticText; read;
end;
Type
TOutputProgressWizardPage = class(TWizardPage)
  procedure Hide;
  property Msg1Label: TNewStaticText; read;
  property Msg2Label: TNewStaticText; read;
  property ProgressBar: TNewProgressBar; read;
  procedure SetProgress(const Position, Max: Longint);
  procedure SetText(const Msg1, Msg2: String);
  procedure Show;
end;
Type
TOutputMarqueeProgressWizardPage = class(TOutputProgressWizardPage)
  procedure Animate;
  procedure SetProgress(const Position, Max: Longint);
end;
Type
TDownloadWizardPage = class(TOutputProgressWizardPage)
  property AbortButton: TNewButton; read;
  property AbortedByUser: Boolean; read;
  property ShowBaseNameInsteadOfUrl: Boolean; read write;
  procedure Add(const Url, BaseName, RequiredSHA256OfFile: String);
  procedure AddEx(const Url, BaseName, RequiredSHA256OfFile, UserName, Password: String);
  procedure Clear;
  function Download: Int64;
  procedure Show;
end;
Type
TExtractionWizardPage = class(TOutputProgressWizardPage)
  property AbortButton: TNewButton; read;
  property AbortedByUser: Boolean; read;
  property ShowArchiveInsteadOfFile: Boolean; read write;
  procedure Add(const ArchiveFileName, DestDir: String; const FullPaths: Boolean);
  procedure Clear;
  procedure Extract;
  procedure Show;
end;
Const
crHand = 1;// $0001
Var
WizardForm = TWizardForm;
Var
UninstallProgressForm = TUninstallProgressForm;
Type
TArrayOfString = array of String;
Type
TArrayOfChar = array of Char;
Type
TArrayOfBoolean = array of Boolean;
Type
TArrayOfInteger = array of Integer;
Type
DWORD = LongWord;
Type
UINT = LongWord;
Type
BOOL = LongBool;
Type
DWORD_PTR = LongWord;
Type
UINT_PTR = LongWord;
Type
INT_PTR = Longint;
Type
TFileTime = record  dwLowDateTime: DWORD;  dwHighDateTime: DWORD;end;
Type
TMsgBoxType = (mbInformation, mbConfirmation, mbError, mbCriticalError);
Type
TSetupMessageID = (msgAbortRetryIgnoreCancel, msgAbortRetryIgnoreSelectAction, msgAbortRetryIgnoreIgnore, msgAbortRetryIgnoreRetry, msgAboutSetupMenuItem, msgAboutSetupMessage, msgAboutSetupNote, msgAboutSetupTitle, msgAdminPrivilegesRequired, msgApplicationsFound, msgApplicationsFound2, msgBadDirName32, msgBadGroupName, msgBeveledLabel, msgBrowseDialogLabel, msgBrowseDialogTitle, msgButtonBack, msgButtonBrowse, msgButtonCancel, msgButtonFinish, msgButtonInstall, msgButtonNewFolder, msgButtonNext, msgButtonNo, msgButtonNoToAll, msgButtonOK, msgButtonStopDownload, msgButtonStopExtraction, msgButtonWizardBrowse, msgButtonYes, msgButtonYesToAll, msgCannotContinue, msgCannotInstallToNetworkDrive, msgCannotInstallToUNCPath, msgChangeDiskTitle, msgClickFinish, msgClickNext, msgCloseApplications, msgCompactInstallation, msgComponentSize1, msgComponentSize2, msgComponentsDiskSpaceGBLabel, msgComponentsDiskSpaceMBLabel, msgConfirmDeleteSharedFile2, msgConfirmDeleteSharedFileTitle, msgConfirmTitle, msgConfirmUninstall, msgCustomInstallation, msgDirDoesntExist, msgDirDoesntExistTitle, msgDirExists, msgDirExistsTitle, msgDirNameTooLong, msgDiskSpaceGBLabel, msgDiskSpaceMBLabel, msgDiskSpaceWarning, msgDiskSpaceWarningTitle, msgDontCloseApplications, msgDownloadingLabel, msgErrorChangingAttr, msgErrorCloseApplications, msgErrorCopying, msgErrorCreatingDir, msgErrorCreatingTemp, msgErrorDownloadAborted, msgErrorDownloadFailed, msgErrorDownloadSizeFailed, msgErrorExecutingProgram, msgErrorExtractionAborted, msgErrorExtractionFailed, msgErrorFileHash1, msgErrorFileHash2, msgErrorFileSize, msgErrorFunctionFailed, msgErrorFunctionFailedNoCode, msgErrorFunctionFailedWithMessage, msgErrorIniEntry, msgErrorInternal2, msgErrorOpeningReadme, msgErrorProgress, msgErrorReadingExistingDest, msgErrorReadingSource, msgErrorRegCreateKey, msgErrorRegisterServer, msgErrorRegisterTypeLib, msgErrorRegOpenKey, msgErrorRegSvr32Failed, msgErrorRegWriteKey, msgErrorRenamingTemp, msgErrorReplacingExistingFile, msgErrorRestartingComputer, msgErrorRestartReplace, msgErrorTitle, msgErrorTooManyFilesInDir, msgExistingFileNewerSelectAction, msgExistingFileNewer2, msgExistingFileNewerOverwriteExisting, msgExistingFileNewerKeepExisting, msgExistingFileNewerOverwriteOrKeepAll, msgExistingFileReadOnly2, msgExistingFileReadOnlyRetry, msgExistingFileReadOnlyKeepExisting, msgExitSetupMessage, msgExitSetupTitle, msgExtractionLabel, msgFileAbortRetryIgnoreSkipNotRecommended, msgFileAbortRetryIgnoreIgnoreNotRecommended, msgFileExistsSelectAction, msgFileExists2, msgFileExistsOverwriteExisting, msgFileExistsKeepExisting, msgFileExistsOverwriteOrKeepAll, msgFileNotInDir2, msgFinishedHeadingLabel, msgFinishedLabel, msgFinishedLabelNoIcons, msgFinishedRestartLabel, msgFinishedRestartMessage, msgFullInstallation, msgGroupNameTooLong, msgHelpTextNote, msgIncorrectPassword, msgInfoAfterClickLabel, msgInfoAfterLabel, msgInfoBeforeClickLabel, msgInfoBeforeLabel, msgInformationTitle, msgInstallingLabel, msgInvalidDirName, msgInvalidDrive, msgInvalidGroupName, msgInvalidParameter, msgInvalidPath, msgLastErrorMessage, msgLdrCannotCreateTemp, msgLdrCannotExecTemp, msgLicenseAccepted, msgLicenseLabel, msgLicenseLabel3, msgLicenseNotAccepted, msgMustEnterGroupName, msgNewFolderName, msgNoProgramGroupCheck2, msgNoRadio, msgNotOnThisPlatform, msgNoUninstallWarning, msgNoUninstallWarningTitle, msgOnlyAdminCanUninstall, msgOnlyOnTheseArchitectures, msgOnlyOnThisPlatform, msgPasswordEditLabel, msgPasswordLabel1, msgPasswordLabel3, msgPathLabel, msgPowerUserPrivilegesRequired, msgPrepareToInstallNeedsRestart, msgPreparingDesc, msgPreviousInstallNotCompleted, msgPrivilegesRequiredOverrideTitle, msgPrivilegesRequiredOverrideInstruction, msgPrivilegesRequiredOverrideText1, msgPrivilegesRequiredOverrideText2, msgPrivilegesRequiredOverrideAllUsers, msgPrivilegesRequiredOverrideAllUsersRecommended, msgPrivilegesRequiredOverrideCurrentUser, msgPrivilegesRequiredOverrideCurrentUserRecommended, msgReadyLabel1, msgReadyLabel2a, msgReadyLabel2b, msgReadyMemoComponents, msgReadyMemoDir, msgReadyMemoGroup, msgReadyMemoTasks, msgReadyMemoType, msgReadyMemoUserInfo, msgRunEntryExec, msgRunEntryShellExec, msgSelectComponentsDesc, msgSelectComponentsLabel2, msgSelectDirBrowseLabel, msgSelectDirDesc, msgSelectDirectoryLabel, msgSelectDirLabel3, msgSelectDiskLabel2, msgSelectLanguageLabel, msgSelectLanguageTitle, msgSelectStartMenuFolderBrowseLabel, msgSelectStartMenuFolderDesc, msgSelectStartMenuFolderLabel3, msgSelectTasksDesc, msgSelectTasksLabel2, msgSetupAborted, msgSetupAlreadyRunning, msgSetupAppRunningError, msgSetupAppTitle, msgSetupFileCorrupt, msgSetupFileCorruptOrWrongVer, msgSetupFileMissing, msgSetupLdrStartupMessage, msgSetupWindowTitle, msgSharedFileNameLabel, msgSharedFileLocationLabel, msgShowReadmeCheck, msgShutdownBlockReasonInstallingApp, msgShutdownBlockReasonUninstallingApp, msgSourceDoesntExist, msgSourceIsCorrupted, msgStatusClosingApplications, msgStatusCreateDirs, msgStatusCreateIcons, msgStatusCreateIniEntries, msgStatusCreateRegistryEntries, msgStatusExtractFiles, msgStatusRegisterFiles, msgStatusRestartingApplications, msgStatusRollback, msgStatusSavingUninstall, msgStatusRunProgram, msgStatusUninstalling, msgStopDownload, msgStopExtraction, msgTranslatorNote, msgUninstallAppFullTitle, msgUninstallAppTitle, msgUninstallDataCorrupted, msgUninstallDisplayNameMark, msgUninstallDisplayNameMarks, msgUninstallDisplayNameMark32Bit, msgUninstallDisplayNameMark64Bit, msgUninstallDisplayNameMarkAllUsers, msgUninstallDisplayNameMarkCurrentUser, msgUninstalledAll, msgUninstalledAndNeedsRestart, msgUninstalledMost, msgUninstallAppRunningError, msgUninstallNotFound, msgUninstallOnlyOnWin64, msgUninstallOpenError, msgUninstallStatusLabel, msgUninstallUnknownEntry, msgUninstallUnsupportedVer, msgUserInfoDesc, msgUserInfoName, msgUserInfoNameRequired, msgUserInfoOrg, msgUserInfoSerial, msgWelcomeLabel1, msgWelcomeLabel2, msgWindowsServicePackRequired, msgWindowsVersionNotSupported, msgWinVersionTooHighError, msgWinVersionTooLowError, msgWizardInfoAfter, msgWizardInfoBefore, msgWizardInstalling, msgWizardLicense, msgWizardPassword, msgWizardPreparing, msgWizardReady, msgWizardSelectDir, msgWizardSelectComponents, msgWizardSelectProgramGroup, msgWizardSelectTasks, msgWizardUninstalling, msgWizardUserInfo, msgYesRadio);
Type
TSetupStep = (ssPreInstall, ssInstall, ssPostInstall, ssDone);
Type
TUninstallStep = (usAppMutexCheck, usUninstall, usPostUninstall, usDone);
Type
TSetupProcessorArchitecture = (paUnknown, paX86, paX64, paArm32, paArm64);
Type
TDotNetVersion = (net11, net20, net30, net35, net4Client, net4Full, net45, net451, net452, net46, net461, net462, net47, net471, net472, net48, net481);
Type
TSplitType = (stAll, stExcludeEmpty, stExcludeLastEmpty);
Type
TExecWait = (ewNoWait, ewWaitUntilTerminated, ewWaitUntilIdle);
Type
TExecOutput = record  StdOut: TArrayOfString;  StdErr: TArrayOfString;  Error: Boolean;end;
Type
TFindRec = record  Name: String;  Attributes: LongWord;  SizeHigh: LongWord;  SizeLow: LongWord;  CreationTime: TFileTime;  LastAccessTime: TFileTime;  LastWriteTime: TFileTime;  AlternateName: String;  FindHandle: THandle;end;
Type
TWindowsVersion = record  Major: Cardinal;  Minor: Cardinal;  Build: Cardinal;  ServicePackMajor: Cardinal;  ServicePackMinor: Cardinal;  NTPlatform: Boolean;  ProductType: Byte;  SuiteMask: Word;end;
Type
TOnDownloadProgress = function(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
Type
TOnExtractionProgress = function(const ArchiveName, FileName: String; const Progress, ProgressMax: Int64): Boolean;
Type
TOnLog = procedure(const S: String; const Error, FirstLine: Boolean);
function PageFromID(const ID: Integer): TWizardPage;
function PageIndexFromID(const ID: Integer): Integer;
function CreateCustomPage(const AfterID: Integer; const ACaption, ADescription: String): TWizardPage;
function CreateInputQueryPage(const AfterID: Integer; const ACaption, ADescription, ASubCaption: String): TInputQueryWizardPage;
function CreateInputOptionPage(const AfterID: Integer; const ACaption, ADescription, ASubCaption: String; Exclusive, ListBox: Boolean): TInputOptionWizardPage;
function CreateInputDirPage(const AfterID: Integer; const ACaption, ADescription, ASubCaption: String; AAppendDir: Boolean; ANewFolderName: String): TInputDirWizardPage;
function CreateInputFilePage(const AfterID: Integer; const ACaption, ADescription, ASubCaption: String): TInputFileWizardPage;
function CreateOutputMsgPage(const AfterID: Integer; const ACaption, ADescription, AMsg: String): TOutputMsgWizardPage;
function CreateOutputMsgMemoPage(const AfterID: Integer; const ACaption, ADescription, ASubCaption: String; const AMsg: AnsiString): TOutputMsgMemoWizardPage;
function CreateOutputProgressPage(const ACaption, ADescription: String): TOutputProgressWizardPage;
function CreateOutputMarqueeProgressPage(const ACaption, ADescription: String): TOutputMarqueeProgressWizardPage;
function CreateDownloadPage(const ACaption, ADescription: String; const OnDownloadProgress: TOnDownloadProgress): TDownloadWizardPage;
function CreateExtractionPage(const ACaption, ADescription: String; const OnExtractionProgress: TOnExtractionProgress): TExtractionWizardPage;
function ScaleX(X: Integer): Integer;
function ScaleY(Y: Integer): Integer;
function CreateCustomForm: TSetupForm;
function SelectDisk(const DiskNumber: Integer; const AFilename: String; var Path: String): Boolean;
function BrowseForFolder(const Prompt: String; var Directory: String; const NewFolderButton: Boolean): Boolean;
function GetOpenFileName(const Prompt: String; var FileName: String; const InitialDirectory, Filter, DefaultExtension: String): Boolean;
function GetOpenFileNameMulti(const Prompt: String; const FileNameList: TStrings; const InitialDirectory, Filter, DefaultExtension: String): Boolean;
function GetSaveFileName(const Prompt: String; var FileName: String; const InitialDirectory, Filter, DefaultExtension: String): Boolean;
function MinimizePathName(const Filename: String; const Font: TFont; MaxLen: Integer): String;
function FileExists(const Name: String): Boolean;
function DirExists(const Name: String): Boolean;
function FileOrDirExists(const Name: String): Boolean;
function GetIniString(const Section, Key, Default, Filename: String): String;
function GetIniInt(const Section, Key: String; const Default, Min, Max: LongInt; const Filename: String): LongInt;
function GetIniBool(const Section, Key: String; const Default: Boolean; const Filename: String): Boolean;
function IniKeyExists(const Section, Key, Filename: String): Boolean;
function IsIniSectionEmpty(const Section, Filename: String): Boolean;
function SetIniString(const Section, Key, Value, Filename: String): Boolean;
function SetIniInt(const Section, Key: String; const Value: LongInt; const Filename: String): Boolean;
function SetIniBool(const Section, Key: String; const Value: Boolean; const Filename: String): Boolean;
procedure DeleteIniEntry(const Section, Key, Filename: String);
procedure DeleteIniSection(const Section, Filename: String);
function GetEnv(const EnvVar: String): String;
function GetCmdTail: String;
function ParamCount: Integer;
function ParamStr(Index: Integer): String;
function AddBackslash(const S: String): String;
function RemoveBackslash(const S: String): String;
function RemoveBackslashUnlessRoot(const S: String): String;
function AddQuotes(const S: String): String;
function RemoveQuotes(const S: String): String;
function GetShortName(const LongName: String): String;
function GetWinDir: String;
function GetSystemDir: String;
function GetSysWow64Dir: String;
function GetSysNativeDir: String;
function GetTempDir: String;
function StringChange(var S: String; const FromStr, ToStr: String): Integer;
function StringChangeEx(var S: String; const FromStr, ToStr: String; const SupportDBCS: Boolean): Integer;
function UsingWinNT: Boolean;
function CopyFile(const ExistingFile, NewFile: String; const FailIfExists: Boolean): Boolean;
function FileCopy(const ExistingFile, NewFile: String; const FailIfExists: Boolean): Boolean;
function ConvertPercentStr(var S: String): Boolean;
function RegValueExists(const RootKey: Integer; const SubKeyName, ValueName: String): Boolean;
function RegQueryStringValue(const RootKey: Integer; const SubKeyName, ValueName: String; var ResultStr: String): Boolean;
function RegQueryMultiStringValue(const RootKey: Integer; const SubKeyName, ValueName: String; var ResultStr: String): Boolean;
function RegDeleteKeyIncludingSubkeys(const RootKey: Integer; const SubkeyName: String): Boolean;
function RegDeleteKeyIfEmpty(const RootKey: Integer; const SubkeyName: String): Boolean;
function RegKeyExists(const RootKey: Integer; const SubKeyName: String): Boolean;
function RegDeleteValue(const RootKey: Integer; const SubKeyName, ValueName: String): Boolean;
function RegGetSubkeyNames(const RootKey: Integer; const SubKeyName: String; var Names: TArrayOfString): Boolean;
function RegGetValueNames(const RootKey: Integer; const SubKeyName: String; var Names: TArrayOfString): Boolean;
function RegQueryDWordValue(const RootKey: Integer; const SubKeyName, ValueName: String; var ResultDWord: Cardinal): Boolean;
function RegQueryBinaryValue(const RootKey: Integer; const SubKeyName, ValueName: String; var ResultStr: AnsiString): Boolean;
function RegWriteStringValue(const RootKey: Integer; const SubKeyName, ValueName, Data: String): Boolean;
function RegWriteExpandStringValue(const RootKey: Integer; const SubKeyName, ValueName, Data: String): Boolean;
function RegWriteMultiStringValue(const RootKey: Integer; const SubKeyName, ValueName, Data: String): Boolean;
function RegWriteDWordValue(const RootKey: Integer; const SubKeyName, ValueName: String; const Data: Cardinal): Boolean;
function RegWriteBinaryValue(const RootKey: Integer; const SubKeyName, ValueName: String; const Data: AnsiString): Boolean;
function IsAdmin: Boolean;
function IsAdminLoggedOn: Boolean;
function IsPowerUserLoggedOn: Boolean;
function IsAdminInstallMode: Boolean;
function FontExists(const FaceName: String): Boolean;
function GetUILanguage: Integer;
function AddPeriod(const S: String): String;
function CharLength(const S: String; const Index: Integer): Integer;
function SetNTFSCompression(const FileOrDir: String; Compress: Boolean): Boolean;
function IsWildcard(const Pattern: String): Boolean;
function WildcardMatch(const Text, Pattern: String): Boolean;
procedure ExtractTemporaryFile(const FileName: String);
function ExtractTemporaryFiles(const Pattern: String): Integer;
function DownloadTemporaryFile(const Url, FileName, RequiredSHA256OfFile: String; const OnDownloadProgress: TOnDownloadProgress): Int64;
function DownloadTemporaryFileSize(const Url: String): Int64;
function DownloadTemporaryFileDate(const Url: String): String;
procedure SetDownloadCredentials(const User, Pass: String);
function CheckForMutexes(Mutexes: String): Boolean;
function DecrementSharedCount(const Is64Bit: Boolean; const Filename: String): Boolean;
procedure DelayDeleteFile(const Filename: String; const Tries: Integer);
function DelTree(const Path: String; const IsDir, DeleteFiles, DeleteSubdirsAlso: Boolean): Boolean;
function GenerateUniqueName(Path: String; const Extension: String): String;
function GetComputerNameString: String;
function GetMD5OfFile(const Filename: String): String;
function GetMD5OfString(const S: AnsiString): String;
function GetMD5OfUnicodeString(const S: String): String;
function GetSHA1OfFile(const Filename: String): String;
function GetSHA1OfString(const S: AnsiString): String;
function GetSHA1OfUnicodeString(const S: String): String;
function GetSHA256OfFile(const Filename: String): String;
function GetSHA256OfString(const S: AnsiString): String;
function GetSHA256OfUnicodeString(const S: String): String;
function GetSpaceOnDisk(const DriveRoot: String; const InMegabytes: Boolean; var Free, Total: Cardinal): Boolean;
function GetSpaceOnDisk64(const DriveRoot: String; var Free, Total: Int64): Boolean;
function GetUserNameString: String;
procedure IncrementSharedCount(const Is64Bit: Boolean; const Filename: String; const AlreadyExisted: Boolean);
function Exec(const Filename, Params, WorkingDir: String; const ShowCmd: Integer; const Wait: TExecWait; var ResultCode: Integer): Boolean;
function ExecAndCaptureOutput(const Filename, Params, WorkingDir: String; const ShowCmd: Integer; const Wait: TExecWait; var ResultCode: Integer; var Output: TExecOutput): Boolean;
function ExecAndLogOutput(const Filename, Params, WorkingDir: String; const ShowCmd: Integer; const Wait: TExecWait; var ResultCode: Integer; const OnLog: TOnLog): Boolean;
function ExecAsOriginalUser(const Filename, Params, WorkingDir: String; const ShowCmd: Integer; const Wait: TExecWait; var ResultCode: Integer): Boolean;
function ShellExec(const Verb, Filename, Params, WorkingDir: String; const ShowCmd: Integer; const Wait: TExecWait; var ErrorCode: Integer): Boolean;
function ShellExecAsOriginalUser(const Verb, Filename, Params, WorkingDir: String; const ShowCmd: Integer; const Wait: TExecWait; var ErrorCode: Integer): Boolean;
function IsProtectedSystemFile(const Filename: String): Boolean;
function MakePendingFileRenameOperationsChecksum: String;
function ModifyPifFile(const Filename: String; const CloseOnExit: Boolean): Boolean;
procedure RegisterServer(const Is64Bit: Boolean; const Filename: String; const FailCriticalErrors: Boolean);
function UnregisterServer(const Is64Bit: Boolean; const Filename: String; const FailCriticalErrors: Boolean): Boolean;
procedure UnregisterFont(const FontName, FontFilename: String; const PerUserFont: Boolean);
procedure RestartReplace(const TempFile, DestFile: String);
function ForceDirectories(Dir: String): Boolean;
function CreateShellLink(const Filename, Description, ShortcutTo, Parameters, WorkingDir, IconFilename: String; const IconIndex, ShowCmd: Integer): String;
procedure RegisterTypeLibrary(const Is64Bit: Boolean; const Filename: String);
function UnregisterTypeLibrary(const Is64Bit: Boolean; const Filename: String): Boolean;
function UnpinShellLink(const Filename: String): Boolean;
function ActiveLanguage: String;
function ExpandConstant(const S: String): String;
function ExpandConstantEx(const S: String; const CustomConst, CustomValue: String): String;
function ExitSetupMsgBox: Boolean;
function GetShellFolderByCSIDL(const Folder: Integer; const Create: Boolean): String;
function InstallOnThisVersion(const MinVersion, OnlyBelowVersion: String): Boolean;
function GetWindowsVersion: Cardinal;
function GetWindowsVersionString: String;
function MsgBox(const Text: String; const Typ: TMsgBoxType; const Buttons: Integer): Integer;
function SuppressibleMsgBox(const Text: String; const Typ: TMsgBoxType; const Buttons, Default: Integer): Integer;
function TaskDialogMsgBox(const Instruction, Text: String; const Typ: TMsgBoxType; const Buttons: Cardinal; const ButtonLabels: TArrayOfString; const ShieldButton: Integer): Integer;
function SuppressibleTaskDialogMsgBox(const Instruction, Text: String; const Typ: TMsgBoxType; const Buttons: Cardinal; const ButtonLabels: TArrayOfString; const ShieldButton: Integer; const Default: Integer): Integer;
function IsWin64: Boolean;
function Is64BitInstallMode: Boolean;
function ProcessorArchitecture: TSetupProcessorArchitecture;
function IsArm32Compatible: Boolean;
function IsArm64: Boolean;
function IsX64: Boolean;
function IsX64OS: Boolean;
function IsX64Compatible: Boolean;
function IsX86: Boolean;
function IsX86OS: Boolean;
function IsX86Compatible: Boolean;
function CustomMessage(const MsgName: String): String;
function RmSessionStarted: Boolean;
function RegisterExtraCloseApplicationsResource(const DisableFsRedir: Boolean; const AFilename: String): Boolean;
function GetWizardForm: TWizardForm;
function WizardIsComponentSelected(const Components: String): Boolean;
function IsComponentSelected(const Components: String): Boolean;
function WizardIsTaskSelected(const Tasks: String): Boolean;
function IsTaskSelected(const Tasks: String): Boolean;
function SetupMessage(const ID: TSetupMessageID): String;
function Random(const Range: Integer): Integer;
function FileSize(const Name: String; var Size: Integer): Boolean;
function FileSize64(const Name: String; var Size: Int64): Boolean;
procedure Set8087CW(NewCW: Word);
function Get8087CW: Word;
function UTF8Encode(const S: String): AnsiString;
function UTF8Decode(const S: AnsiString): String;
procedure Beep;
function TrimLeft(const S: String): String;
function TrimRight(const S: String): String;
function GetCurrentDir: String;
function SetCurrentDir(const Dir: String): Boolean;
function ExpandFileName(const FileName: String): String;
function ExpandUNCFileName(const FileName: String): String;
function ExtractRelativePath(const BaseName, DestName: String): String;
function ExtractFileDir(const FileName: String): String;
function ExtractFileDrive(const FileName: String): String;
function ExtractFileExt(const FileName: String): String;
function ExtractFileName(const FileName: String): String;
function ExtractFilePath(const FileName: String): String;
function ChangeFileExt(const FileName, Extension: String): String;
function FileSearch(const Name, DirList: String): String;
function RenameFile(const OldName, NewName: String): Boolean;
function DeleteFile(const FileName: String): Boolean;
function CreateDir(const Dir: String): Boolean;
function RemoveDir(const Dir: String): Boolean;
function CompareStr(const S1, S2: String): Integer;
function CompareText(const S1, S2: String): Integer;
function SameStr(const S1, S2: String): Boolean;
function SameText(const S1, S2: String): Boolean;
function GetDateTimeString(const DateTimeFormat: String; const DateSeparator, TimeSeparator: Char): String;
function SysErrorMessage(ErrorCode: Integer): String;
function GetVersionNumbers(const Filename: String; var VersionMS, VersionLS: Cardinal): Boolean;
function GetVersionComponents(const Filename: String; var Major, Minor, Revision, Build: Word): Boolean;
function GetVersionNumbersString(const Filename: String; var Version: String): Boolean;
function GetPackedVersion(const Filename: String; var Version: Int64): Boolean;
function PackVersionNumbers(const VersionMS, VersionLS: Cardinal): Int64;
function PackVersionComponents(const Major, Minor, Revision, Build: Word): Int64;
function ComparePackedVersion(const Version1, Version2: Int64): Integer;
function SamePackedVersion(const Version1, Version2: Int64): Boolean;
procedure UnpackVersionNumbers(const Version: Int64; var VersionMS, VersionLS: Cardinal);
procedure UnpackVersionComponents(const Version: Int64; var Major, Minor, Revision, Build: Word);
function VersionToStr(const Version: Int64): String;
function StrToVersion(const VersionString: String; var Version: Int64): Boolean;
procedure Sleep(const Milliseconds: LongInt);
function FindWindowByClassName(const ClassName: String): HWND;
function FindWindowByWindowName(const WindowName: String): HWND;
function SendMessage(const Wnd: HWND; const Msg, WParam, LParam: LongInt): LongInt;
function PostMessage(const Wnd: HWND; const Msg, WParam, LParam: LongInt): Boolean;
function SendNotifyMessage(const Wnd: HWND; const Msg, WParam, LParam: LongInt): Boolean;
function RegisterWindowMessage(const Name: String): LongInt;
function SendBroadcastMessage(const Msg, WParam, LParam: LongInt): LongInt;
function PostBroadcastMessage(const Msg, WParam, LParam: LongInt): Boolean;
function SendBroadcastNotifyMessage(const Msg, WParam, LParam: LongInt): Boolean;
function LoadDLL(const DLLName: String; var ErrorCode: Integer): LongInt;
function CallDLLProc(const DLLHandle: LongInt; const ProcName: String; const Param1, Param2: LongInt; var Result: LongInt): Boolean;
function FreeDLL(const DLLHandle: LongInt): Boolean;
procedure CreateMutex(const Name: String);
procedure OemToCharBuff(var S: AnsiString);
procedure CharToOemBuff(var S: AnsiString);
procedure CoFreeUnusedLibraries;
procedure Log(const S: String);
procedure BringToFrontAndRestore;
function WizardDirValue: String;
function WizardGroupValue: String;
function WizardNoIcons: Boolean;
function WizardSetupType(const Description: Boolean): String;
function WizardSelectedComponents(const Descriptions: Boolean): String;
function WizardSelectedTasks(const Descriptions: Boolean): String;
procedure WizardSelectComponents(const Components: String);
procedure WizardSelectTasks(const Tasks: String);
function WizardSilent: Boolean;
function IsUninstaller: Boolean;
function UninstallSilent: Boolean;
function CurrentFilename: String;
function CurrentSourceFilename: String;
function CastStringToInteger(var S: String): LongInt;
function CastIntegerToString(const L: LongInt): String;
procedure Abort;
function GetExceptionMessage: String;
procedure RaiseException(const Msg: String);
procedure ShowExceptionMessage;
function Terminated: Boolean;
function GetPreviousData(const ValueName, DefaultValueData: String): String;
function SetPreviousData(const PreviousDataKey: Integer; const ValueName, ValueData: String): Boolean;
function LoadStringFromFile(const FileName: String; var S: AnsiString): Boolean;
function LoadStringFromLockedFile(const FileName: String; var S: AnsiString): Boolean;
function LoadStringsFromFile(const FileName: String; var S: TArrayOfString): Boolean;
function LoadStringsFromLockedFile(const FileName: String; var S: TArrayOfString): Boolean;
function SaveStringToFile(const FileName: String; const S: AnsiString; const Append: Boolean): Boolean;
function SaveStringsToFile(const FileName: String; const S: TArrayOfString; const Append: Boolean): Boolean;
function SaveStringsToUTF8File(const FileName: String; const S: TArrayOfString; const Append: Boolean): Boolean;
function SaveStringsToUTF8FileWithoutBOM(const FileName: String; const S: TArrayOfString; const Append: Boolean): Boolean;
function EnableFsRedirection(const Enable: Boolean): Boolean;
function GetUninstallProgressForm: TUninstallProgressForm;
function CreateCallback(Method: AnyMethod): Longword;
function IsDotNetInstalled(const MinVersion: TDotNetVersion; const MinServicePack: Cardinal): Boolean;
function IsMsiProductInstalled(const UpgradeCode: String; const PackedMinVersion: Int64): Boolean;
function InitializeBitmapImageFromIcon(const BitmapImage: TBitmapImage; const IconFilename: String; const BkColor: TColor; const AscendingTrySizes: TArrayOfInteger): Boolean;
procedure Extract7ZipArchive(const ArchiveFileName, DestDir: String; const FullPaths: Boolean; const OnExtractionProgress: TOnExtractionProgress);
function Debugging: Boolean;
function StringJoin(const Separator: String; const Values: TArrayOfString): String;
function StringSplit(const S: String; const Separators: TArrayOfString; const Typ: TSplitType): TArrayOfString;
function StringSplitEx(const S: String; const Separators: TArrayOfString; const Quote: Char; const Typ: TSplitType): TArrayOfString;
function FmtMessage(const S: String; const Args: array of String): String;
function FindFirst(const FileName: String; var FindRec: TFindRec): Boolean;
function FindNext(var FindRec: TFindRec): Boolean;
procedure FindClose(var FindRec: TFindRec);
function Format(const Format: String; const Args: array of const): String;
procedure GetWindowsVersionEx(var Version: TWindowsVersion);
Const
MaxInt = 2147483647;// $7FFFFFFF
Const
irInstall = 1;// $0001
Const
wpWelcome = 1;// $0001
Const
wpLicense = 2;// $0002
Const
wpPassword = 3;// $0003
Const
wpInfoBefore = 4;// $0004
Const
wpUserInfo = 5;// $0005
Const
wpSelectDir = 6;// $0006
Const
wpSelectComponents = 7;// $0007
Const
wpSelectProgramGroup = 8;// $0008
Const
wpSelectTasks = 9;// $0009
Const
wpReady = 10;// $000A
Const
wpPreparing = 11;// $000B
Const
wpInstalling = 12;// $000C
Const
wpInfoAfter = 13;// $000D
Const
wpFinished = 14;// $000E
Const
MB_OK = 0;// $0000
Const
MB_OKCANCEL = 1;// $0001
Const
MB_ABORTRETRYIGNORE = 2;// $0002
Const
MB_YESNOCANCEL = 3;// $0003
Const
MB_YESNO = 4;// $0004
Const
MB_RETRYCANCEL = 5;// $0005
Const
MB_DEFBUTTON1 = 0;// $0000
Const
MB_DEFBUTTON2 = 256;// $0100
Const
MB_DEFBUTTON3 = 512;// $0200
Const
MB_SETFOREGROUND = 65536;// $10000
Const
IDOK = 1;// $0001
Const
IDCANCEL = 2;// $0002
Const
IDABORT = 3;// $0003
Const
IDRETRY = 4;// $0004
Const
IDIGNORE = 5;// $0005
Const
IDYES = 6;// $0006
Const
IDNO = 7;// $0007
Const
HWND_BROADCAST = 65535;// $FFFF
Const
HKEY_AUTO = 1;// $0001
Const
HKEY_AUTO_32 = 16777217;// $1000001
Const
HKEY_AUTO_64 = 33554433;// $2000001
Const
HKEY_CLASSES_ROOT = -2147483648;// $80000000
Const
HKEY_CLASSES_ROOT_32 = -2130706432;// $81000000
Const
HKEY_CLASSES_ROOT_64 = -2113929216;// $82000000
Const
HKEY_CURRENT_USER = -2147483647;// $80000001
Const
HKEY_CURRENT_USER_32 = -2130706431;// $81000001
Const
HKEY_CURRENT_USER_64 = -2113929215;// $82000001
Const
HKEY_LOCAL_MACHINE = -2147483646;// $80000002
Const
HKEY_LOCAL_MACHINE_32 = -2130706430;// $81000002
Const
HKEY_LOCAL_MACHINE_64 = -2113929214;// $82000002
Const
HKEY_USERS = -2147483645;// $80000003
Const
HKEY_USERS_32 = -2130706429;// $81000003
Const
HKEY_USERS_64 = -2113929213;// $82000003
Const
HKEY_PERFORMANCE_DATA = -2147483644;// $80000004
Const
HKEY_CURRENT_CONFIG = -2147483643;// $80000005
Const
HKEY_CURRENT_CONFIG_32 = -2130706427;// $81000005
Const
HKEY_CURRENT_CONFIG_64 = -2113929211;// $82000005
Const
HKEY_DYN_DATA = -2147483642;// $80000006
Const
HKA = 1;// $0001
Const
HKA32 = 16777217;// $1000001
Const
HKA64 = 33554433;// $2000001
Const
HKCR = -2147483648;// $80000000
Const
HKCR32 = -2130706432;// $81000000
Const
HKCR64 = -2113929216;// $82000000
Const
HKCU = -2147483647;// $80000001
Const
HKCU32 = -2130706431;// $81000001
Const
HKCU64 = -2113929215;// $82000001
Const
HKLM = -2147483646;// $80000002
Const
HKLM32 = -2130706430;// $81000002
Const
HKLM64 = -2113929214;// $82000002
Const
HKU = -2147483645;// $80000003
Const
HKU32 = -2130706429;// $81000003
Const
HKU64 = -2113929213;// $82000003
Const
HKCC = -2147483643;// $80000005
Const
HKCC32 = -2130706427;// $81000005
Const
HKCC64 = -2113929211;// $82000005
Const
SW_HIDE = 0;// $0000
Const
SW_SHOWNORMAL = 1;// $0001
Const
SW_SHOWMINIMIZED = 2;// $0002
Const
SW_SHOWMAXIMIZED = 3;// $0003
Const
SW_SHOWMINNOACTIVE = 7;// $0007
Const
SW_SHOW = 5;// $0005
Const
FILE_ATTRIBUTE_READONLY = 1;// $0001
Const
FILE_ATTRIBUTE_HIDDEN = 2;// $0002
Const
FILE_ATTRIBUTE_SYSTEM = 4;// $0004
Const
FILE_ATTRIBUTE_DIRECTORY = 16;// $0010
Const
FILE_ATTRIBUTE_ARCHIVE = 32;// $0020
Const
FILE_ATTRIBUTE_DEVICE = 64;// $0040
Const
FILE_ATTRIBUTE_NORMAL = 128;// $0080
Const
FILE_ATTRIBUTE_TEMPORARY = 256;// $0100
Const
FILE_ATTRIBUTE_SPARSE_FILE = 512;// $0200
Const
FILE_ATTRIBUTE_REPARSE_POINT = 1024;// $0400
Const
FILE_ATTRIBUTE_COMPRESSED = 2048;// $0800
Const
FILE_ATTRIBUTE_OFFLINE = 4096;// $1000
Const
FILE_ATTRIBUTE_NOT_CONTENT_INDEXED = 8192;// $2000
Const
FILE_ATTRIBUTE_ENCRYPTED = 16384;// $4000
Const
VER_NT_WORKSTATION = 1;// $0001
Const
VER_NT_DOMAIN_CONTROLLER = 2;// $0002
Const
VER_NT_SERVER = 3;// $0003
Const
VER_SUITE_SMALLBUSINESS = 1;// $0001
Const
VER_SUITE_ENTERPRISE = 2;// $0002
Const
VER_SUITE_BACKOFFICE = 4;// $0004
Const
VER_SUITE_COMMUNICATIONS = 8;// $0008
Const
VER_SUITE_TERMINAL = 16;// $0010
Const
VER_SUITE_SMALLBUSINESS_RESTRICTED = 32;// $0020
Const
VER_SUITE_EMBEDDEDNT = 64;// $0040
Const
VER_SUITE_DATACENTER = 128;// $0080
Const
VER_SUITE_SINGLEUSERTS = 256;// $0100
Const
VER_SUITE_PERSONAL = 512;// $0200
Const
VER_SUITE_BLADE = 1024;// $0400
Const
VER_SUITE_EMBEDDED_RESTRICTED = 2048;// $0800
Const
VER_SUITE_SECURITY_APPLIANCE = 4096;// $1000
