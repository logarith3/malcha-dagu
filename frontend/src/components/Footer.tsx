

export default function Footer() {
    return (
        <footer className="w-full bg-gray-50 py-8 border-t border-gray-100 mt-12">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {/* 서비스 정보 */}
                    <div>
                        <h3 className="text-sm font-semibold text-gray-900 mb-2">DAGU</h3>
                        <p className="text-xs text-gray-500">
                            악기 시세를 한눈에, 다구에서 판단하세요.
                        </p>
                        <p className="text-xs text-gray-400 mt-2">
                            문의나 오류발생시 이쪽으로 연락주세요.
                            <br />
                            <br />
                            contact: malchalabs@gmail.com
                        </p>
                    </div>

                    {/* 필수 고지 사항 */}
                    <div className="text-xs text-gray-400 space-y-2">
                        <p>
                            <strong>1. 책임의 한계</strong><br />
                            본 서비스는 가격 정보 제공을 목적으로 하며, 실제 구매 및 거래에 대한 책임은 각 판매자 및 구매자에게 있습니다.
                            DAGU는 상품의 품질, 상태, 거래 결과에 대해 일절 책임지지 않습니다.
                        </p>
                        <p>
                            <strong>2. 정보의 정확성</strong><br />
                            표시된 가격 정보는 검색 시점 기준이며, 판매처 사정에 따라 실시간으로 변경될 수 있습니다.
                            실제 구매 전 반드시 판매처에서 가격 및 상품 정보를 확인하시기 바랍니다.
                        </p>
                        <p>
                            <strong>3. 외부 링크 면책</strong><br />
                            본 서비스는 외부 사이트(네이버, 뮬, 리버브 등)로의 링크를 제공할 수 있으며,
                            해당 사이트에서 이루어지는 상품 판매, 결제, 배송 및 거래에 대해 DAGU는 직접적인 책임을 지지 않습니다.
                        </p>
                        <p>
                            <strong>4. 이용자 판단 책임</strong><br />
                            본 서비스에서 제공하는 가격 정보 및 비교 결과는 참고용이며,
                            구매 여부에 대한 최종 판단은 이용자 본인의 책임입니다.
                        </p>
                    </div>
                </div>

                <div className="mt-8 pt-8 border-t border-gray-200">
                    <p className="text-xs text-center text-gray-400">
                        &copy; {new Date().getFullYear()} malchalab. All rights reserved.
                    </p>
                </div>
            </div>
        </footer>
    );
}
