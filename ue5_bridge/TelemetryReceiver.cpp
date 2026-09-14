#include "TelemetryReceiver.h"
#include "SocketSubsystem.h"
#include "Serialization/JsonSerializer.h"
#include "Dom/JsonObject.h"

UTelemetryReceiver::UTelemetryReceiver()
{
    PrimaryComponentTick.bCanEverTick = true;
}

void UTelemetryReceiver::BeginPlay()
{
    Super::BeginPlay();

    FIPv4Endpoint Endpoint(FIPv4Address::Any, ListenPort);
    ListenSocket = FUdpSocketBuilder(TEXT("SIH_TelemetryReceiver"))
        .AsNonBlocking()
        .AsReusable()
        .BoundToEndpoint(Endpoint)
        .WithReceiveBufferSize(65536)
        .Build();
}

void UTelemetryReceiver::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (ListenSocket)
    {
        ListenSocket->Close();
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(ListenSocket);
        ListenSocket = nullptr;
    }

    Super::EndPlay(EndPlayReason);
}

void UTelemetryReceiver::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);
    ReadIncomingPackets();
}

void UTelemetryReceiver::ReadIncomingPackets()
{
    if (!ListenSocket) return;

    uint32 PendingDataSize = 0;
    while (ListenSocket->HasPendingData(PendingDataSize))
    {
        TArray<uint8> Buffer;
        Buffer.SetNumUninitialized(PendingDataSize);

        int32 BytesRead = 0;
        TSharedRef<FInternetAddr> Sender = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->CreateInternetAddr();
        if (ListenSocket->RecvFrom(Buffer.GetData(), Buffer.Num(), BytesRead, *Sender) && BytesRead > 0)
        {
            Buffer.SetNum(BytesRead);
            Buffer.Add(0);
            FString JsonStr = UTF8_TO_TCHAR(reinterpret_cast<const char*>(Buffer.GetData()));
            TSharedPtr<FJsonObject> JsonObject;
            TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(JsonStr);

            if (FJsonSerializer::Deserialize(Reader, JsonObject) && JsonObject.IsValid())
            {
                const TArray<TSharedPtr<FJsonValue>>* TargetArray;
                if (JsonObject->TryGetArrayField(TEXT("targets"), TargetArray))
                {
                    ActiveTargets.Empty();
                    for (const auto& Val : *TargetArray)
                    {
                        TSharedPtr<FJsonObject> TargetObj = Val->AsObject();
                        if (TargetObj.IsValid())
                        {
                            FTrackedTargetInfo Info;
                            Info.TargetId = TargetObj->GetIntegerField(TEXT("id"));
                            // Convert meters to Unreal centimeters
                            Info.WorldLocation = FVector(
                                TargetObj->GetNumberField(TEXT("x")) * 100.0f,
                                TargetObj->GetNumberField(TEXT("y")) * 100.0f,
                                TargetObj->GetNumberField(TEXT("z")) * 100.0f
                            );
                            Info.Speed = TargetObj->GetNumberField(TEXT("speed"));
                            Info.Heading = TargetObj->GetNumberField(TEXT("heading"));
                            Info.State = TargetObj->GetStringField(TEXT("state"));

                            ActiveTargets.Add(Info);
                        }
                    }

                    OnTelemetryUpdated.Broadcast(ActiveTargets);
                }

                // Parse Designated Structure & Obstacle Survey Data
                const TSharedPtr<FJsonObject>* StructObjPtr = nullptr;
                if (JsonObject->TryGetObjectField(TEXT("designated_structure"), StructObjPtr) && StructObjPtr && (*StructObjPtr).IsValid())
                {
                    TSharedPtr<FJsonObject> SObj = *StructObjPtr;
                    DesignatedStructure.StructureId = SObj->GetStringField(TEXT("id"));
                    DesignatedStructure.StructureName = SObj->GetStringField(TEXT("name"));
                    DesignatedStructure.StructureType = SObj->GetStringField(TEXT("type"));

                    // Convert meters to Unreal centimeters
                    float PosX = SObj->GetNumberField(TEXT("x")) * 100.0f;
                    float PosY = SObj->GetNumberField(TEXT("y")) * 100.0f;
                    float Length = SObj->GetNumberField(TEXT("length"));
                    float Width = SObj->GetNumberField(TEXT("width"));
                    float Height = SObj->GetNumberField(TEXT("height"));
                    float PosZ = (Height * 100.0f) / 2.0f;

                    DesignatedStructure.WorldLocation = FVector(PosX, PosY, PosZ);
                    DesignatedStructure.LengthMeters = Length;
                    DesignatedStructure.WidthMeters = Width;
                    DesignatedStructure.HeightMeters = Height;
                    DesignatedStructure.FootprintAreaSqM = Length * Width;
                    DesignatedStructure.Sector = SObj->GetStringField(TEXT("sector"));

                    double Clr = 0.0;
                    if (SObj->TryGetNumberField(TEXT("clearance"), Clr) && Clr > 0.0)
                    {
                        DesignatedStructure.ClearanceMeters = (float)Clr;
                        DesignatedStructure.bIsUnderpass = true;
                    }
                    else
                    {
                        DesignatedStructure.ClearanceMeters = 0.0f;
                        DesignatedStructure.bIsUnderpass = false;
                    }

                    DesignatedStructure.bIsActive = true;
                    bHasDesignatedStructure = true;
                    OnStructureDesignated.Broadcast(DesignatedStructure);
                }
                else if (JsonObject->HasField(TEXT("designated_structure")) && JsonObject->HasTypedField<EJson::Null>(TEXT("designated_structure")))
                {
                    if (bHasDesignatedStructure)
                    {
                        DesignatedStructure = FStructureSurveyInfo();
                        bHasDesignatedStructure = false;
                        OnStructureDesignated.Broadcast(DesignatedStructure);
                    }
                }
            }
        }
    }
}
