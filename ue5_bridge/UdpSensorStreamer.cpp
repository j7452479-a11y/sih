#include "UdpSensorStreamer.h"
#include "Engine/World.h"
#include "DrawDebugHelpers.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "SocketSubsystem.h"
#include "EngineUtils.h"
#include "Components/SplineComponent.h"

UUdpSensorStreamer::UUdpSensorStreamer()
{
    PrimaryComponentTick.bCanEverTick = false;
}

void UUdpSensorStreamer::LocateAndBindSpline()
{
    if (FollowSplineTag.IsEmpty() || !GetWorld()) return;

    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        AActor* Actor = *It;
        if (Actor->GetActorLabel().Contains(FollowSplineTag) || Actor->Tags.Contains(FName(*FollowSplineTag)))
        {
            USplineComponent* Spline = Actor->FindComponentByClass<USplineComponent>();
            if (Spline)
            {
                CachedSplineComp = Spline;
                break;
            }
        }
    }
}

void UUdpSensorStreamer::BeginPlay()
{
    Super::BeginPlay();

    LocateAndBindSpline();

    // 1. Initialize UDP Socket (only if transmitting sensor data)
    if (NumChannels > 0)
    {
        ISocketSubsystem* SocketSubsystem = ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM);
        RemoteEndpoint = SocketSubsystem->CreateInternetAddr();

        bool bIsValidIP = false;
        RemoteEndpoint->SetIp(*TargetIP, bIsValidIP);
        RemoteEndpoint->SetPort(TargetPort);

        SenderSocket = FUdpSocketBuilder(TEXT("SIH_UdpSender"))
            .AsNonBlocking()
            .AsReusable()
            .WithSendBufferSize(65536)
            .Build();
    }

    // 2. Start 20 Hz Scan / Navigation Timer
    float Interval = 1.0f / ScanFrequencyHz;
    GetWorld()->GetTimerManager().SetTimer(ScanTimerHandle, this, &UUdpSensorStreamer::FireLiDARScan, Interval, true);
}

void UUdpSensorStreamer::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    GetWorld()->GetTimerManager().ClearTimer(ScanTimerHandle);

    if (SenderSocket)
    {
        SenderSocket->Close();
        ISocketSubsystem::Get(PLATFORM_SOCKETSUBSYSTEM)->DestroySocket(SenderSocket);
        SenderSocket = nullptr;
    }

    Super::EndPlay(EndPlayReason);
}

void UUdpSensorStreamer::FireLiDARScan()
{
    if (!GetOwner()) return;

    // 1. Advance owner actor along patrol spline
    if (CachedSplineComp.IsValid())
    {
        CurrentSplineDistance += (PatrolSpeedMps * 100.0f) * (1.0f / ScanFrequencyHz);
        float SplineLength = CachedSplineComp->GetSplineLength();
        if (SplineLength > 0.0f)
        {
            if (CurrentSplineDistance > SplineLength)
            {
                CurrentSplineDistance -= SplineLength;
            }
            FVector NewLoc = CachedSplineComp->GetLocationAtDistanceAlongSpline(CurrentSplineDistance, ESplineCoordinateSpace::World);
            FRotator NewRot = CachedSplineComp->GetRotationAtDistanceAlongSpline(CurrentSplineDistance, ESplineCoordinateSpace::World);
            GetOwner()->SetActorLocationAndRotation(NewLoc, NewRot);
        }
    }
    else if (!FollowSplineTag.IsEmpty())
    {
        LocateAndBindSpline();
    }

    // If movement-only (e.g. hostile combatant) or socket uninitialized, return early
    if (NumChannels <= 0 || !SenderSocket) return;

    FVector SensorOrigin = GetOwner()->GetActorLocation();
    FRotator SensorRotation = GetOwner()->GetActorRotation();

    TArray<FSIHPoint> HitPoints;
    HitPoints.Reserve(NumChannels);

    FCollisionQueryParams TraceParams(FName(TEXT("LiDARTrace")), true, GetOwner());
    TraceParams.bReturnPhysicalMaterial = true;

    // Conical nadir sweep for UAV (or planar for UGV)
    for (int32 i = 0; i < NumChannels; ++i)
    {
        float AzimuthAngle = (360.0f / NumChannels) * i;
        float PitchAngle = (SensorType == 1) ? -85.0f : (i % 8 - 4) * 3.0f; // UAV looks down, UGV looks ahead

        FRotator BeamRot = SensorRotation + FRotator(PitchAngle, AzimuthAngle, 0.0f);
        FVector TraceEnd = SensorOrigin + (BeamRot.Vector() * (MaxRangeMeters * 100.0f)); // UE5 uses cm

        FHitResult Hit;
        if (GetWorld()->LineTraceSingleByChannel(Hit, SensorOrigin, TraceEnd, ECC_Visibility, TraceParams))
        {
            FSIHPoint Pt;
            // Convert Unreal centimeters to SI engine meters
            Pt.X = Hit.ImpactPoint.X / 100.0f;
            Pt.Y = Hit.ImpactPoint.Y / 100.0f;
            Pt.Z = Hit.ImpactPoint.Z / 100.0f;

            // Semantic classification via Actor tags first
            Pt.SemanticClass = 0; // Default Ground
            if (Hit.GetActor())
            {
                for (const FName& Tag : Hit.GetActor()->Tags)
                {
                    FString TagStr = Tag.ToString();
                    if (TagStr.StartsWith(TEXT("BLD-")) || TagStr.StartsWith(TEXT("WAL-")) || TagStr.StartsWith(TEXT("BNK-")) || TagStr.StartsWith(TEXT("TWR-")))
                    {
                        Pt.SemanticClass = 2; // Obstacle / Building
                        break;
                    }
                    else if (TagStr.StartsWith(TEXT("BRG-")))
                    {
                        Pt.SemanticClass = 3; // Bridge
                        break;
                    }
                    else if (TagStr.Contains(TEXT("Target")) || TagStr.Contains(TEXT("Hostile")))
                    {
                        Pt.SemanticClass = 8; // Hostile Target
                        break;
                    }
                    else if (TagStr.StartsWith(TEXT("ROAD-")))
                    {
                        Pt.SemanticClass = 1; // Road / Cobblestone
                        break;
                    }
                }
            }

            // Fallback to Physical Material if tags unassigned
            if (Pt.SemanticClass == 0 && Hit.PhysMaterial.IsValid())
            {
                FString MatName = Hit.PhysMaterial->GetName();
                if (MatName.Contains(TEXT("Target"))) Pt.SemanticClass = 8;       // Hostile
                else if (MatName.Contains(TEXT("Bridge"))) Pt.SemanticClass = 3;  // Overhang
                else if (MatName.Contains(TEXT("Obstacle"))) Pt.SemanticClass = 2;// Wall/Building
                else if (MatName.Contains(TEXT("Road"))) Pt.SemanticClass = 1;    // Cobblestone
            }

            HitPoints.Add(Pt);

            // Real-time LiDAR laser beam visualizer in PIE
            if (bDrawDebugBeams && (i % 2 == 0))
            {
                FColor BeamColor = (Pt.SemanticClass == 8) ? FColor::Red :
                                   (Pt.SemanticClass == 3) ? FColor::Yellow :
                                   (Pt.SemanticClass == 2) ? FColor(0, 240, 255) : FColor(0, 150, 255);
                DrawDebugLine(GetWorld(), SensorOrigin, Hit.ImpactPoint, BeamColor, false, 0.05f, 0, 1.2f);
            }
        }
    }

    if (HitPoints.Num() == 0) return;

    // Pack Binary 25-byte header
    FSIHHeader Header;
    FMemory::Memcpy(Header.Magic, "SIH1", 4);
    Header.FrameId = ++CurrentFrameId;
    Header.Timestamp = FPlatformTime::Seconds();
    Header.SensorType = SensorType;
    Header.PointCount = HitPoints.Num();
    Header.Checksum = 0;

    // Transmit over UDP
    TArray<uint8> PacketBuffer;
    PacketBuffer.SetNumUninitialized(sizeof(FSIHHeader) + (HitPoints.Num() * sizeof(FSIHPoint)));

    FMemory::Memcpy(PacketBuffer.GetData(), &Header, sizeof(FSIHHeader));
    FMemory::Memcpy(PacketBuffer.GetData() + sizeof(FSIHHeader), HitPoints.GetData(), HitPoints.Num() * sizeof(FSIHPoint));

    int32 BytesSent = 0;
    SenderSocket->SendTo(PacketBuffer.GetData(), PacketBuffer.Num(), BytesSent, *RemoteEndpoint);
}
