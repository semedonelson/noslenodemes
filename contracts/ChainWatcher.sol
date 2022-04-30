// SPDX-License-Identifier: UNLICENSED

pragma solidity >=0.6.6 <0.8.0;

import "../interfaces/IUniswapV2Router02.sol";
import "../interfaces/IUniswapV2Pair.sol";
import "../interfaces/IUniswapV2Factory.sol";
import "../interfaces/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "../library/LowGasSafeMath.sol";

contract ChainWatcher is Ownable {
    using LowGasSafeMath for uint256;
    using LowGasSafeMath for int256;

    constructor() public {}

    function getReservers(address pairAddress)
        public
        view
        returns (uint256 reserve0, uint256 reserve1)
    {
        (reserve0, reserve1, ) = IUniswapV2Pair(pairAddress).getReserves();
    }

    function validate(
        address[] memory tokens,
        uint256[] memory amounts,
        address[] memory routers
    )
        public
        view
        onlyOwner
        returns (
            int256 profit,
            uint256 amount,
            address[] memory result
        )
    {
        result = new address[](2);
        profit = 0;
        amount = 0;
        (profit, amount) = check(
            tokens[0],
            amounts[1],
            tokens[1],
            routers[0],
            routers[1]
        );
        if (profit > 0) {
            result[0] = tokens[0];
            result[1] = tokens[1];
        } else {
            (profit, amount) = check(
                tokens[1],
                amounts[0],
                tokens[0],
                routers[1],
                routers[0]
            );
            if (profit > 0) {
                result[1] = tokens[0];
                result[0] = tokens[1];
            }
        }
    }

    function check(
        address _tokenBorrow, // example: BUSD
        uint256 _amountTokenPay, // example: BNB => 10 * 1e18
        address _tokenPay, // example: BNB
        address _sourceRouter,
        address _targetRouter
    ) public view onlyOwner returns (int256, uint256) {
        address[] memory path1 = new address[](2);
        address[] memory path2 = new address[](2);
        path1[0] = path2[1] = _tokenPay;
        path1[1] = path2[0] = _tokenBorrow;

        uint256 amountOut = IUniswapV2Router02(_sourceRouter).getAmountsOut(
            _amountTokenPay,
            path1
        )[1];

        uint256 amountRepay = amountOut > 0
            ? IUniswapV2Router02(_targetRouter).getAmountsOut(amountOut, path2)[
                1
            ]
            : 0;
        return (
            int256(
                LowGasSafeMath.sub(int256(amountRepay), int256(_amountTokenPay))
            ), // our profit or loss; example output: BNB amount
            amountOut // the amount we get from our input "_amountTokenPay"; example: BUSD amount
        );
    }

    function getAmountsOut(
        address router,
        uint256 amount,
        address[] memory tokens
    ) public view onlyOwner returns (uint256 amountOut) {
        amountOut = IUniswapV2Router02(router).getAmountsOut(amount, tokens)[1];
    }
}
