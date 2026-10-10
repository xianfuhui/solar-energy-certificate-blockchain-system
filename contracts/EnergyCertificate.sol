// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title EnergyCertificate - Chức năng 5: cấp chứng chỉ năng lượng từ sản lượng điện đã kiểm tra
/// @notice Hợp đồng KHÔNG tin dữ liệu một nguồn: nhận 3 số đo từ 3 oracle, tự kiểm tra lại độ lệch
///         và chỉ cấp chứng chỉ khi AI không gắn cờ bất thường.
/// @dev Phạm vi hiện tại: đăng ký dự án + cấp chứng chỉ (mục 1-5).
///      Chống cấp trùng, chuyển nhượng, thu hồi (mục 6-8) sẽ bổ sung ở bước sau.
contract EnergyCertificate {
    struct Project {
        address owner;        // tài khoản nhận chứng chỉ
        uint32 capacityKw;    // công suất DC (kW)
        bool registered;
    }

    struct Certificate {
        uint256 id;
        uint32 projectId;
        uint32 date;          // YYYYMMDD
        uint256 energyWh;     // sản lượng đã được xác thực (Wh) = trung vị 3 oracle
        address owner;
        uint64 issuedAt;
    }

    address public admin;
    uint256 public toleranceBps;                 // độ lệch tối đa so với trung vị (10000 = 100%)
    mapping(address => bool) public issuers;     // tài khoản backend được phép gửi yêu cầu cấp
    mapping(uint32 => Project) public projects;

    Certificate[] private certificates;          // id = index + 1
    mapping(address => uint256[]) private certsOfOwner;

    event ProjectRegistered(uint32 indexed projectId, address indexed owner, uint32 capacityKw);
    event CertificateIssued(
        uint256 indexed certId, uint32 indexed projectId, uint32 date, uint256 energyWh, address indexed owner
    );
    event ToleranceChanged(uint256 toleranceBps);
    event IssuerSet(address indexed issuer, bool allowed);

    modifier onlyAdmin() { require(msg.sender == admin, "not admin"); _; }
    modifier onlyIssuer() { require(issuers[msg.sender], "not issuer"); _; }

    constructor(uint256 _toleranceBps) {
        require(_toleranceBps > 0 && _toleranceBps <= 10000, "bad tolerance");
        admin = msg.sender;
        issuers[msg.sender] = true;
        toleranceBps = _toleranceBps;
    }

    // ---------- Quản trị ----------
    function setIssuer(address who, bool allowed) external onlyAdmin {
        issuers[who] = allowed;
        emit IssuerSet(who, allowed);
    }

    function setTolerance(uint256 bps) external onlyAdmin {
        require(bps > 0 && bps <= 10000, "bad tolerance");
        toleranceBps = bps;
        emit ToleranceChanged(bps);
    }

    function registerProject(uint32 projectId, address owner, uint32 capacityKw) external onlyAdmin {
        require(!projects[projectId].registered, "project exists");
        require(owner != address(0) && capacityKw > 0, "bad params");
        projects[projectId] = Project(owner, capacityKw, true);
        emit ProjectRegistered(projectId, owner, capacityKw);
    }

    // ---------- Cấp chứng chỉ ----------
    /// @param readingsWh sản lượng ngày (Wh) do 3 oracle báo cáo: [điện kế, inverter, mô hình bức xạ]
    /// @param aiFlagged  true nếu hệ thống AI đã đánh dấu ngày này là bất thường
    function issueCertificate(
        uint32 projectId,
        uint32 date,
        uint256[3] calldata readingsWh,
        bool aiFlagged
    ) external onlyIssuer returns (uint256 certId) {
        Project memory p = projects[projectId];
        require(p.registered, "unknown project");
        require(date >= 20100101 && date <= 20991231, "bad date");
        require(!aiFlagged, "flagged by AI");

        uint256 med = _median3(readingsWh[0], readingsWh[1], readingsWh[2]);
        require(med > 0, "zero energy");
        // Giới hạn vật lý: không thể vượt công suất DC x 24h
        require(med <= uint256(p.capacityKw) * 24 * 1000, "exceeds capacity");
        for (uint256 i = 0; i < 3; i++) {
            uint256 diff = readingsWh[i] > med ? readingsWh[i] - med : med - readingsWh[i];
            require(diff * 10000 <= med * toleranceBps, "oracle mismatch");
        }

        certificates.push(Certificate(certificates.length + 1, projectId, date, med, p.owner, uint64(block.timestamp)));
        certId = certificates.length;
        certsOfOwner[p.owner].push(certId);
        emit CertificateIssued(certId, projectId, date, med, p.owner);
    }

    // ---------- Truy vấn ----------
    function totalCertificates() external view returns (uint256) { return certificates.length; }

    function getCertificate(uint256 certId) external view returns (Certificate memory) {
        require(certId >= 1 && certId <= certificates.length, "no such cert");
        return certificates[certId - 1];
    }

    function certificatesOf(address owner) external view returns (uint256[] memory) {
        return certsOfOwner[owner];
    }

    function _median3(uint256 a, uint256 b, uint256 c) private pure returns (uint256) {
        if ((a >= b && a <= c) || (a <= b && a >= c)) return a;
        if ((b >= a && b <= c) || (b <= a && b >= c)) return b;
        return c;
    }
}
