#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Networking.h"
#include "Sockets.h"
#include "UdpSensorStreamer.generated.h"

#pragma pack(push, 1)
struct FSIHHeader
{
    char Magic[4];          // "SIH1"
    uint32 FrameId;
    double Timestamp;
    uint8 SensorType;       // 1 = UAV, 2 = UGV
    uint32 PointCount;
    uint32 Checksum;
};

struct FSIHPoint
{
    float X;
    float Y;
    float Z;
    uint8 SemanticClass;    // 0=Ground, 1=Road, 2=Obstacle, 3=Bridge, 8=Target
    uint8 Padding[3];
};
#pragma pack(pop)

UCLASS(ClassGroup=(Custom), meta=(BlueprintSpawnableComponent))
class SIH_PERCEPTION_API UUdpSensorStreamer : public UActorComponent
{
    GENERATED_BODY()

public:
    UUdpSensorStreamer();

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Network")
    FString TargetIP = TEXT("127.0.0.1");

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Network")
    int32 TargetPort = 5001; // 5001 for UAV, 5002 for UGV

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Sensor")
    uint8 SensorType = 1; // 1 = UAV, 2 = UGV

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Sensor")
    int32 NumChannels = 32;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Sensor")
    float MaxRangeMeters = 100.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Sensor")
    float ScanFrequencyHz = 20.0f;

    /** Optional actor label/tag of a Spline actor to follow autonomously (e.g. BP_UAV_FlightPath_Spline) */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Navigation")
    FString FollowSplineTag = TEXT("");

    /** Patrol movement speed along spline in meters per second (e.g. 5.0 for UAV, 3.0 for UGV, 1.5 for Hostile) */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Navigation")
    float PatrolSpeedMps = 5.0f;

    /** Whether to draw debug laser lines during LiDAR scan in PIE */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "SIH Sensor")
    bool bDrawDebugBeams = true;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    FSocket* SenderSocket = nullptr;
    TSharedPtr<FInternetAddr> RemoteEndpoint;
    FTimerHandle ScanTimerHandle;
    uint32 CurrentFrameId = 0;

    TWeakObjectPtr<class USplineComponent> CachedSplineComp = nullptr;
    float CurrentSplineDistance = 0.0f;
    void LocateAndBindSpline();

    void FireLiDARScan();
};
